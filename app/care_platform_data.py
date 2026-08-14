"""Mock hospice back-office system — one per fictional hospice brand.

This is deliberately a *separate* pretend system from BetterMesh itself: it
stands in for a hospice's own EMR-adjacent record system (the thing that,
per the pitch, already holds the DME need as a physician's order/care-plan
line-item). "Dispatch Equipment" here sends that already-structured need to
BetterMesh via the /webhook/pre-discharge-order endpoint — no free text, no
parsing, matching the pivot away from NL order intake.

All patients and clinical details below are synthetic. No real PHI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class HospiceBrand:
    slug: str
    name: str
    hostname: str
    tagline: str
    logo: str  # filename under /static/logos/
    # Every site has identical functionality (dispatch / a-la-carte order /
    # mark-deceased). This is just which patient+action to walk through when
    # demoing on this hospice's site — not a restriction on what it can do.
    suggested_journey: str
    # Palette: bg (page background), panel (card background), ink (primary
    # text), accent (brand color), accent_ink (text on accent), muted.
    bg: str
    panel: str
    ink: str
    accent: str
    accent_ink: str
    muted: str
    line: str


HOSPICES: dict[str, HospiceBrand] = {
    "anchorpoint": HospiceBrand(
        slug="anchorpoint",
        name="Anchorpoint Hospice Partners",
        hostname="anchorpoint.theslyon.com",
        tagline="Care Record System",
        logo="anchorpoint.png",
        suggested_journey="Miriam Castellano (PT-89112) — routine pre-discharge dispatch",
        bg="#f4f3f7",
        panel="#ffffff",
        ink="#232135",
        accent="#1f3a5f",
        accent_ink="#f0c987",
        muted="#6b6880",
        line="#dedbe8",
    ),
    "cedarridge": HospiceBrand(
        slug="cedarridge",
        name="Cedar Ridge Hospice & Home Care",
        hostname="cedarridge.theslyon.com",
        tagline="Patient Care Portal",
        logo="cedarridge.png",
        suggested_journey="Walter Osei (PT-89204) — mid-stay a-la-carte equipment order",
        bg="#f3f0e8",
        panel="#fffdf8",
        ink="#2b3327",
        accent="#3f5d43",
        accent_ink="#f3ead9",
        muted="#6f7a68",
        line="#dcd4c0",
    ),
    "thistlemoor": HospiceBrand(
        slug="thistlemoor",
        name="Thistlemoor Hospice",
        hostname="thistlemoor.theslyon.com",
        tagline="Clinical Chart",
        logo="thistlemoor.png",
        suggested_journey="Agnes Pruitt (PT-87950) — mark deceased, watch pickup dispatch",
        bg="#f8f1f2",
        panel="#fffbfb",
        ink="#382a37",
        accent="#5c3a5e",
        accent_ink="#f6dfe1",
        muted="#8a7688",
        line="#e6d6dd",
    ),
}

HOSTNAME_TO_SLUG = {b.hostname: b.slug for b in HOSPICES.values()}
DEFAULT_HOSPICE_SLUG = "anchorpoint"


@dataclass
class EquipmentNeed:
    code: str  # HCPCS E-code
    name: str
    ordered_by: str
    ordered_date: str
    dispatched: bool = False
    urgent: bool = False


@dataclass
class Patient:
    id: str
    name: str
    dob: str
    mrn: str
    hospice_slug: str
    admission_date: str
    primary_diagnosis: str
    care_level: str
    case_manager: str
    physician: str
    equipment_needs: list[EquipmentNeed] = field(default_factory=list)
    status: str = "Active in Care"  # or "Deceased" — Thistlemoor's demo toggles this


def _in(days: int, hour: int = 14, minute: int = 0) -> str:
    dt = datetime.now() + timedelta(days=days)
    return dt.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()


def _hours(n: int) -> str:
    dt = datetime.now() + timedelta(hours=n)
    return dt.replace(second=0, microsecond=0).isoformat()


PATIENTS: dict[str, Patient] = {
    # --- Anchorpoint: existing BetterMesh patients (already dispatched) ---
    "PT-88421": Patient(
        id="PT-88421", name="Thomas Delacroix", dob="1948-03-11", mrn="AP-40217",
        hospice_slug="anchorpoint", admission_date="2026-08-12", primary_diagnosis="CHF, end-stage",
        care_level="Routine Home Care", case_manager="Renee Okafor, RN", physician="Dr. A. Whitfield",
        equipment_needs=[EquipmentNeed("E0250", "Hospital Bed", "Dr. A. Whitfield", "2026-08-12", dispatched=True)],
    ),
    "PT-88502": Patient(
        id="PT-88502", name="Carol Iwu", dob="1955-11-02", mrn="AP-40289",
        hospice_slug="anchorpoint", admission_date="2026-08-13", primary_diagnosis="COPD, severe",
        care_level="Continuous Home Care", case_manager="Renee Okafor, RN", physician="Dr. M. Sandoval",
        equipment_needs=[EquipmentNeed("E0601", "CPAP / Oxygen Concentrator", "Dr. M. Sandoval", "2026-08-13", dispatched=True)],
    ),
    "PT-88710": Patient(
        id="PT-88710", name="Harold Fennimore", dob="1941-07-19", mrn="AP-40301",
        hospice_slug="anchorpoint", admission_date="2026-08-14", primary_diagnosis="COPD exacerbation",
        care_level="Routine Home Care", case_manager="Devon Marsh, RN", physician="Dr. M. Sandoval",
        equipment_needs=[EquipmentNeed("E0601", "CPAP / Oxygen Concentrator", "Dr. M. Sandoval", "2026-08-14", dispatched=True)],
    ),
    # NEW — fresh dispatch demo patient for Anchorpoint
    "PT-89112": Patient(
        id="PT-89112", name="Miriam Castellano", dob="1952-09-24", mrn="AP-40355",
        hospice_slug="anchorpoint", admission_date="2026-08-14", primary_diagnosis="Metastatic breast cancer",
        care_level="Routine Home Care", case_manager="Devon Marsh, RN", physician="Dr. A. Whitfield",
        equipment_needs=[EquipmentNeed("E1130", "Wheelchair", "Dr. A. Whitfield", "2026-08-14", dispatched=False)],
    ),

    # --- Cedar Ridge: existing (already dispatched) ---
    "PT-88190": Patient(
        id="PT-88190", name="Nadia Petrov", dob="1960-01-30", mrn="CR-71042",
        hospice_slug="cedarridge", admission_date="2026-08-11", primary_diagnosis="ALS",
        care_level="Routine Home Care", case_manager="Sam Lindqvist, RN", physician="Dr. K. Obuya",
        equipment_needs=[EquipmentNeed("E1130", "Wheelchair", "Dr. K. Obuya", "2026-08-11", dispatched=True)],
    ),
    "PT-87720": Patient(
        id="PT-87720", name="Earl Whitcombe", dob="1937-05-08", mrn="CR-71005",
        hospice_slug="cedarridge", admission_date="2026-08-05", primary_diagnosis="Advanced dementia",
        care_level="Routine Home Care", case_manager="Sam Lindqvist, RN", physician="Dr. K. Obuya",
        equipment_needs=[EquipmentNeed("E0250", "Hospital Bed", "Dr. K. Obuya", "2026-08-05", dispatched=True)],
    ),
    # A-LA-CARTE demo patient for Cedar Ridge: established in care, condition
    # has progressed since admission — the equipment need below is context
    # (what the physician already flagged), but the demo interaction is the
    # a-la-carte "Order Equipment" menu, not a pre-filled dispatch panel.
    "PT-89204": Patient(
        id="PT-89204", name="Walter Osei", dob="1944-12-02", mrn="CR-71098",
        hospice_slug="cedarridge", admission_date="2026-07-30", primary_diagnosis="End-stage renal disease",
        care_level="Continuous Home Care", case_manager="Priya Chandran, RN", physician="Dr. L. Fournier",
        equipment_needs=[EquipmentNeed("E0601", "CPAP / Oxygen Concentrator", "Dr. L. Fournier", "2026-08-14", dispatched=False, urgent=True)],
    ),

    # DECEASED demo patient for Thistlemoor: equipment already delivered with a
    # real vendor attached (DME-10087, Sample Vendor 1), so marking her
    # deceased produces a pickup routed to a real vendor, not a null one.
    "PT-87950": Patient(
        id="PT-87950", name="Agnes Pruitt", dob="1933-02-14", mrn="TM-15588",
        hospice_slug="thistlemoor", admission_date="2026-08-02", primary_diagnosis="Advanced Parkinson's",
        care_level="Routine Home Care", case_manager="Ines Faraday, RN", physician="Dr. R. Okonkwo",
        equipment_needs=[EquipmentNeed("E0250", "Hospital Bed", "Dr. R. Okonkwo", "2026-08-02", dispatched=True)],
    ),
}


def patients_for(hospice_slug: str) -> list[Patient]:
    return sorted(
        (p for p in PATIENTS.values() if p.hospice_slug == hospice_slug),
        key=lambda p: p.name,
    )


def default_target_date(order_type: str = "Admission") -> str:
    """A sensible default target for the dispatch panel's deadline field."""
    return _hours(4) if order_type == "STAT" else _in(1, hour=14)
