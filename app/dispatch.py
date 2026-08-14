"""Dispatch logic: an opportunity pool vendors pull from, plus post-death pickup.

Availability is explicit and rules-based on purpose. Each vendor carries a stock
list (which E-codes they hold) and a speed (how fast they can arrive). An order in
the pool is an "opportunity" only to vendors that stock it; each vendor sees a
suggested ETA and whether it meets the target window, then chooses to accept. No
auto-push, no AI: with inventory known, "can I make this window?" is deterministic.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from . import notifications, store
from .models import (
    DELIVERED,
    IN_TRANSIT,
    ORDERED,
    PICKED_UP,
    PICKUP_REQUESTED,
    VENDORS,
    Order,
    Vendor,
)


def _stamp() -> str:
    return datetime.now().strftime("%H:%M")


def suggested_eta(vendor: Vendor, order: Order) -> datetime:
    """When this vendor could realistically arrive, from its speed profile."""
    return datetime.now() + timedelta(minutes=vendor.speed_min)


def meets_window(eta: datetime, order: Order) -> bool:
    """Whether an ETA lands inside the order's target window."""
    return order.target_date is not None and eta <= order.target_date


def opportunities_for(vendor_name: str, orders: list[Order]) -> list[dict]:
    """Open pool orders this vendor can stock, annotated with ETA and meet/miss.

    This is the vendor's 'opportunities' feed: what's available to pull, and
    whether they can hit the window if they take it.
    """
    vendor = VENDORS[vendor_name]
    feed: list[dict] = []
    for o in orders:
        if o.is_open and o.equipment_code in vendor.stock:
            eta = suggested_eta(vendor, o)
            feed.append({"order": o, "eta": eta, "meets": meets_window(eta, o)})
    # Soonest-achievable first.
    return sorted(feed, key=lambda f: f["eta"])


def rank_candidates_for(order: Order) -> list[dict]:
    """Rank contracted vendors for an order: on-time confidence first, price second.

    Every stocking vendor is a candidate, not just the one that happens to
    accept. Vendors that can meet the target window rank ahead of ones that
    can't, regardless of price; soonest ETA is the confidence signal within
    that split; price only breaks ties among comparably-confident vendors.
    This gives the hospice side visibility into the vendor tradeoff even
    though vendors themselves never see each other's price or ranking.
    """
    candidates: list[dict] = []
    for vendor in VENDORS.values():
        if order.equipment_code not in vendor.stock:
            continue
        eta = suggested_eta(vendor, order)
        candidates.append(
            {
                "vendor": vendor.name,
                "eta": eta,
                "meets": meets_window(eta, order),
                "price": vendor.price,
            }
        )
    return sorted(candidates, key=lambda c: (not c["meets"], c["eta"], c["price"]))


def best_candidate_for(order: Order) -> dict | None:
    """The single top-ranked vendor recommendation for an order, if any stock it."""
    ranked = rank_candidates_for(order)
    return ranked[0] if ranked else None


def accept(order: Order, vendor_name: str) -> tuple[bool, str]:
    """A vendor pulls an opportunity off the pool and commits to it."""
    if not order.is_open:
        return False, f"{order.id} is no longer open."
    vendor = VENDORS.get(vendor_name)
    if vendor is None or order.equipment_code not in vendor.stock:
        return False, f"{vendor_name} does not stock {order.equipment_code}."

    eta = suggested_eta(vendor, order)
    order.vendor = vendor_name
    order.eta = eta
    order.status = IN_TRANSIT
    verdict = "within window" if meets_window(eta, order) else "OUTSIDE window"
    order.log.append(
        f"{_stamp()} accepted by {vendor_name}; committed ETA "
        f"{eta.strftime('%-I:%M %p')} ({verdict})"
    )
    notifications.notify_hospice(order, "accepted")
    return True, f"{order.id} accepted by {vendor_name}, ETA {eta.strftime('%-I:%M %p')}."


def rebroadcast(order: Order) -> tuple[bool, str]:
    """Release an at-risk order back into the network opportunity pool.

    The current vendor is dropped and the order becomes open for any contracted
    vendor to pull - this is the hospice's escape hatch when a delivery is slipping.
    """
    if not order.at_risk:
        return False, "Order is not at risk; nothing to re-broadcast."
    prior_vendor = order.vendor
    order.vendor = None
    order.eta = None
    order.status = ORDERED
    order.log.append(
        f"{_stamp()} re-broadcast to network (was slipping on {prior_vendor})"
    )
    return True, f"{order.id} re-broadcast to the network; awaiting a vendor to accept."


def mark_delivered(order: Order) -> tuple[bool, str]:
    """Dispatcher confirms a delivery landed."""
    if order.is_pickup or order.status == DELIVERED:
        return False, "Nothing to deliver."
    order.status = DELIVERED
    order.log.append(f"{_stamp()} delivery confirmed by {order.vendor}")
    notifications.notify_hospice(order, "delivered")
    return True, f"{order.id} marked delivered."


def complete_pickup(order: Order) -> tuple[bool, str]:
    """Dispatcher confirms equipment was picked up from the home."""
    if not order.is_pickup or order.status == PICKED_UP:
        return False, "Nothing to pick up."
    order.status = PICKED_UP
    order.log.append(f"{_stamp()} pickup completed by {order.vendor}")
    notifications.notify_hospice(order, "pickup_completed")
    return True, f"{order.id} pickup completed."


def mark_deceased(patient_id: str) -> tuple[int, list[str]]:
    """Create pickup orders for a deceased patient's delivered equipment.

    This is what replaces the after-death phone call: a status change fans out
    pickup orders into the vendor queue automatically.
    """
    created: list[str] = []
    for order in store.all_orders():
        same_patient = order.patient_id == patient_id
        already_pickup = order.is_pickup
        if same_patient and not already_pickup:
            pickup = Order(
                id=store.next_id(),
                patient_id=patient_id,
                hospice=order.hospice,
                equipment_code=order.equipment_code,
                order_type="Pickup",
                status=PICKUP_REQUESTED,
                ordered_at=datetime.now(),
                # 24h is BetterRX's own stated pickup target (kickoff Q&A,
                # 2026-08-14): the hospice keeps paying for the equipment every
                # day it sits uncollected, so this is a sourced SLA, not a guess.
                target_date=datetime.now() + timedelta(hours=24),
                vendor=order.vendor,
                is_pickup=True,
                address=order.address,
                contact_phone=order.contact_phone,
            )
            pickup.log.append(
                f"{_stamp()} auto-created on death of {patient_id}; "
                f"pickup routed to {order.vendor or 'network'}"
            )
            store.add(pickup)
            created.append(pickup.id)
    return len(created), created

