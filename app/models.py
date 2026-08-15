"""Domain model and in-network vendor profiles for BetterMesh.

Kept deliberately small: one Order dataclass, a closed set of contracted vendors,
and a synthetic inventory table so the Tier 1 path has something to read.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


# Order lifecycle states shown on the shared board.
ORDERED = "Ordered"
DISPATCHED = "Dispatched"
IN_TRANSIT = "In Transit"
DELIVERED = "Delivered"
PICKUP_REQUESTED = "Pickup Requested"
PICKED_UP = "Picked Up"
CANCELLED = "Cancelled"

ACTIVE_DELIVERY_STATES = {ORDERED, DISPATCHED, IN_TRANSIT}
CLOSED_STATES = {DELIVERED, PICKED_UP, CANCELLED}


# HCPCS E-code -> human label. Used by the UI (dropdowns/menus render this dict
# directly). Real, commonly billed home-hospice DME codes.
EQUIPMENT = {
    "E0250": "Hospital Bed",
    "E1130": "Wheelchair",
    "E0601": "CPAP / Oxygen Concentrator",
    "E0143": "Walker, Folding (Wheeled)",
    "E0163": "Bedside Commode",
    "E0570": "Nebulizer",
    "E0305": "Hospital Bed Side Rails",
    "E0630": "Patient Lift, Hydraulic",
    "A6196": "Wound Care Dressing, Alginate",
}


# The hospice's closed contracted network. Each vendor carries a synthetic stock
# list (Tier 1 inventory) so re-dispatch can prefer a vendor that actually has
# the equipment. speed_min is a rough "how fast can they get there" hint. price
# is a synthetic flat rate per delivery (no live vendor pricing API exists today,
# per the bounty FAQ, so this stands in for one the same way stock/speed_min do).
@dataclass
class Vendor:
    name: str
    stock: set[str]
    speed_min: int
    price: float


VENDORS: dict[str, Vendor] = {
    "Sample Vendor 1": Vendor("Sample Vendor 1", {"E0250", "E1130"}, speed_min=90, price=60),
    "Sample Vendor 2": Vendor("Sample Vendor 2", {"E0601", "E0250"}, speed_min=150, price=45),
    "Sample Vendor 3": Vendor("Sample Vendor 3", {"E0250", "E0601", "E1130"}, speed_min=60, price=85),
}


@dataclass
class Order:
    id: str
    patient_id: str
    hospice: str
    equipment_code: str
    order_type: str  # Admission | Routine | STAT | Pickup
    status: str
    ordered_at: datetime
    target_date: datetime | None = None  # discharge window / pickup-by
    vendor: str | None = None
    eta: datetime | None = None
    is_pickup: bool = False
    log: list[str] = field(default_factory=list)
    # What a DME vendor actually needs to fulfill the order: where it goes and
    # who to call. Deliberately not clinical — no diagnosis, no care level.
    # equipment_notes covers the one case where a little clinical detail earns
    # its way in: sizing (bed weight capacity, wheelchair width, O2 flow rate).
    # First name only, not full legal name — enough that a driver or
    # dispatcher can address the person, without carrying more identity than
    # the delivery itself needs.
    patient_first_name: str = ""
    address: str = ""
    contact_phone: str = ""
    equipment_notes: str = ""
    # Whether the patient/family has consented to sharing their info with the
    # DME vendor fulfilling this order. Surfaced to vendors so they know when
    # it's missing; defaults False (opt-in, not assumed).
    consent_on_file: bool = False
    # Caller-supplied idempotency token from the pre-discharge webhook (e.g. a
    # hospice EMR's own order/event id). Empty when an order didn't arrive
    # with one — dedup by external_ref is opt-in, not required.
    external_ref: str = ""

    @property
    def equipment_name(self) -> str:
        return EQUIPMENT.get(self.equipment_code, self.equipment_code)

    @property
    def is_open(self) -> bool:
        """Unassigned delivery order sitting in the network opportunity pool."""
        return self.vendor is None and not self.is_pickup and self.status == ORDERED

    @property
    def at_risk(self) -> bool:
        """A delivery is at risk when its ETA misses the target window."""
        if self.status in CLOSED_STATES or self.is_pickup:
            return False
        if self.eta is None or self.target_date is None:
            return False
        return self.eta > self.target_date
