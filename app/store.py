"""SQLite-backed order store, seeded from the bounty's six sample orders.

Persists to a SQLite file (app/bettermesh.db) instead of an in-memory dict, but
keeps the same tiny function surface (seed/all_orders/get/add/next_id) so callers
never see the difference. seed() still drops and re-inserts every row, so the
demo stays deterministic across restarts and /reset calls.

Implementation note: dispatch.py mutates the Order objects handed back by get()/
all_orders() in place (order.status = ..., order.log.append(...)) rather than
calling add() again - that's how the original in-memory dict store picked up
those edits, since get() returned the very same object the dict held. To keep
that behavior identical, we hold a process-local cache of live Order objects
(so in-place mutations are visible the same way) and flush that cache to SQLite
on every read, which is what gives us real disk persistence on top of it.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from .models import (
    DELIVERED,
    DISPATCHED,
    IN_TRANSIT,
    ORDERED,
    PICKUP_REQUESTED,
    Order,
)

_DB_PATH = Path(__file__).resolve().parent / "bettermesh.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    hospice TEXT NOT NULL,
    equipment_code TEXT NOT NULL,
    order_type TEXT NOT NULL,
    status TEXT NOT NULL,
    ordered_at TEXT NOT NULL,
    target_date TEXT,
    vendor TEXT,
    eta TEXT,
    is_pickup INTEGER NOT NULL,
    log TEXT NOT NULL,
    address TEXT NOT NULL DEFAULT '',
    contact_phone TEXT NOT NULL DEFAULT '',
    equipment_notes TEXT NOT NULL DEFAULT '',
    external_ref TEXT NOT NULL DEFAULT ''
);
"""

_UPSERT_SQL = """
INSERT INTO orders (
    id, patient_id, hospice, equipment_code, order_type, status,
    ordered_at, target_date, vendor, eta, is_pickup, log,
    address, contact_phone, equipment_notes, external_ref
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    patient_id=excluded.patient_id,
    hospice=excluded.hospice,
    equipment_code=excluded.equipment_code,
    order_type=excluded.order_type,
    status=excluded.status,
    ordered_at=excluded.ordered_at,
    target_date=excluded.target_date,
    vendor=excluded.vendor,
    eta=excluded.eta,
    is_pickup=excluded.is_pickup,
    log=excluded.log,
    address=excluded.address,
    contact_phone=excluded.contact_phone,
    equipment_notes=excluded.equipment_notes,
    external_ref=excluded.external_ref
"""

# Process-local cache of live Order objects, mirrored to SQLite. None until
# first touched, so a fresh process picks up whatever's already on disk.
_CACHE: dict[str, Order] | None = None


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(_SCHEMA)
    return conn


def _dt_to_str(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _str_to_dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s is not None else None


def _row_to_order(row: tuple) -> Order:
    (
        id_,
        patient_id,
        hospice,
        equipment_code,
        order_type,
        status,
        ordered_at,
        target_date,
        vendor,
        eta,
        is_pickup,
        log,
        address,
        contact_phone,
        equipment_notes,
        external_ref,
    ) = row
    return Order(
        id=id_,
        patient_id=patient_id,
        hospice=hospice,
        equipment_code=equipment_code,
        order_type=order_type,
        status=status,
        ordered_at=_str_to_dt(ordered_at),
        target_date=_str_to_dt(target_date),
        vendor=vendor,
        eta=_str_to_dt(eta),
        is_pickup=bool(is_pickup),
        log=json.loads(log),
        address=address,
        contact_phone=contact_phone,
        equipment_notes=equipment_notes,
        external_ref=external_ref,
    )


def _order_to_params(order: Order) -> tuple:
    return (
        order.id,
        order.patient_id,
        order.hospice,
        order.equipment_code,
        order.order_type,
        order.status,
        _dt_to_str(order.ordered_at),
        _dt_to_str(order.target_date),
        order.vendor,
        _dt_to_str(order.eta),
        int(order.is_pickup),
        json.dumps(order.log),
        order.address,
        order.contact_phone,
        order.equipment_notes,
        order.external_ref,
    )


def _ensure_cache() -> dict[str, Order]:
    """Lazily hydrate the in-memory cache from SQLite on first use."""
    global _CACHE
    if _CACHE is None:
        with _connect() as conn:
            rows = conn.execute("SELECT * FROM orders").fetchall()
        _CACHE = {row[0]: _row_to_order(row) for row in rows}
    return _CACHE


def _flush() -> None:
    """Write the current cache state to SQLite.

    Called before every read so in-place mutations made by dispatch.py (which
    doesn't call add() again after editing an order) get persisted to disk.
    """
    cache = _ensure_cache()
    with _connect() as conn:
        if cache:
            conn.executemany(_UPSERT_SQL, [_order_to_params(o) for o in cache.values()])


def _today_at(hour: int, minute: int) -> datetime:
    now = datetime.now()
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _mins(delta: int) -> datetime:
    """A time offset from now, so demo scenarios hold regardless of wall-clock."""
    return datetime.now() + timedelta(minutes=delta)


def seed() -> None:
    """Load the six synthetic sample orders from the bounty brief.

    Times are now-relative so the at-risk scenario is always true when demoed.
    """
    global _CACHE
    orders = [
        # 1. Open opportunity: unassigned, plenty of runway (discharge tomorrow).
        Order(
            id="DME-10231",
            patient_id="PT-88421",
            hospice="Anchorpoint Hospice Partners",
            equipment_code="E0250",
            order_type="Admission",
            status=ORDERED,
            ordered_at=_mins(-90),
            target_date=datetime.now().replace(second=0, microsecond=0) + timedelta(days=1),
            address="118 Larkspur Ln, Springfield",
            contact_phone="(555) 201-4487",
        ),
        # 2. Dispatched, routine, on track.
        Order(
            id="DME-10198",
            patient_id="PT-88190",
            hospice="Cedar Ridge Hospice & Home Care",
            equipment_code="E1130",
            order_type="Routine",
            status=DISPATCHED,
            ordered_at=_mins(-120),
            target_date=_mins(120),
            vendor="Sample Vendor 1",
            eta=_mins(80),
            address="47 Birchwood Ct, Springfield",
            contact_phone="(555) 388-2210",
        ),
        # 3. In transit but AT RISK: ETA misses the discharge window. (The star.)
        Order(
            id="DME-10305",
            patient_id="PT-88502",
            hospice="Anchorpoint Hospice Partners",
            equipment_code="E0601",
            order_type="STAT",
            status=IN_TRANSIT,
            ordered_at=_mins(-45),
            target_date=_mins(60),
            vendor="Sample Vendor 2",
            eta=_mins(100),
            address="902 Cardinal Way, Springfield",
            contact_phone="(555) 674-9053",
            equipment_notes="High-flow, 5L/min",
        ),
        # 4. Delivered, closed.
        Order(
            id="DME-10087",
            patient_id="PT-87950",
            hospice="Thistlemoor Hospice",
            equipment_code="E0250",
            order_type="Admission",
            status=DELIVERED,
            ordered_at=_today_at(7, 30) - timedelta(days=1),
            target_date=_today_at(12, 0) - timedelta(days=1),
            vendor="Sample Vendor 1",
            eta=_today_at(11, 15) - timedelta(days=1),
            address="15 Foxglove Ter, Springfield",
            contact_phone="(555) 512-7734",
            equipment_notes="Bariatric frame, 450lb capacity",
        ),
        # 5. Pickup requested after a death (post-death lifecycle stage).
        Order(
            id="DME-10412",
            patient_id="PT-87720",
            hospice="Cedar Ridge Hospice & Home Care",
            equipment_code="E0250",
            order_type="Pickup",
            status=PICKUP_REQUESTED,
            ordered_at=_mins(-30),
            target_date=_mins(360),
            vendor="Sample Vendor 1",
            is_pickup=True,
            address="330 Hollowbrook Dr, Springfield",
            contact_phone="(555) 447-6621",
        ),
        # 6. Open opportunity: STAT, unassigned. Only a fast vendor can meet it.
        Order(
            id="DME-10500",
            patient_id="PT-88710",
            hospice="Anchorpoint Hospice Partners",
            equipment_code="E0601",
            order_type="STAT",
            status=ORDERED,
            ordered_at=_mins(-10),
            target_date=_mins(120),
            address="61 Thistledown Rd, Springfield",
            contact_phone="(555) 293-8814",
            equipment_notes="Portable concentrator preferred, 2nd floor walk-up",
        ),
    ]
    _CACHE = {o.id: o for o in orders}
    with _connect() as conn:
        conn.execute("DELETE FROM orders")
    _flush()


def all_orders() -> list[Order]:
    _flush()
    cache = _ensure_cache()
    return sorted(cache.values(), key=lambda o: o.ordered_at)


def get(order_id: str) -> Order | None:
    _flush()
    cache = _ensure_cache()
    return cache.get(order_id)


def add(order: Order) -> None:
    cache = _ensure_cache()
    cache[order.id] = order
    _flush()


def next_id() -> str:
    cache = _ensure_cache()
    n = 10500 + len(cache)
    while f"DME-{n}" in cache:
        n += 1
    return f"DME-{n}"
