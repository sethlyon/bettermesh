"""Mock hospice back-office system — routes.

Serves three differently-branded read-only-ish patient chart sites (one per
fictional hospice), all from this same deployment. In production each is
reached via its own custom domain (anchorpoint/cedarridge/thistlemoor
.theslyon.com); locally, pass ?hospice=<slug> to preview a given brand since
there's no real subdomain routing on 127.0.0.1.

No login here — this represents a *different* system than BetterMesh, and
isn't the thing being demoed for access control.
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from . import sso
from .care_platform_data import (
    DEFAULT_HOSPICE_SLUG,
    HOSPICES,
    HOSTNAME_TO_SLUG,
    PATIENTS,
    default_target_date,
    patients_for,
)
from .models import EQUIPMENT

router = APIRouter(prefix="/care-platform")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# In-memory inbox of BetterMesh -> hospice push notifications (see
# app/notifications.py), keyed by hospice slug. Newest-last; only the most
# recent 10 per hospice are kept. This is intentionally a demo-simple store,
# not persistence - it resets on process restart, same as the rest of this
# mock system's state.
_RECENT_NOTIFICATIONS: dict[str, list[dict]] = {slug: [] for slug in HOSPICES}


def _resolve_hospice_slug(request: Request) -> str:
    q = request.query_params.get("hospice")
    if q in HOSPICES:
        return q
    host = (request.headers.get("host") or "").split(":")[0]
    return HOSTNAME_TO_SLUG.get(host, DEFAULT_HOSPICE_SLUG)


def _bettermesh_origin(request: Request) -> str:
    """Where BetterMesh's own board lives, from this request's point of view.

    In production every hospice site is a different subdomain from
    bettermesh.theslyon.com, so this must be an absolute URL. Locally
    everything shares one origin (127.0.0.1:8000), so just reuse it.
    """
    host = (request.headers.get("host") or "").split(":")[0]
    if host in ("127.0.0.1", "localhost"):
        return f"{request.url.scheme}://{request.headers.get('host')}"
    return "https://bettermesh.theslyon.com"


def _webhook_secret() -> str:
    return os.environ.get("WEBHOOK_SECRET", "dev-insecure-webhook-secret-change-me")


def _bettermesh_sso_url(request: Request, slug: str, next_path: str) -> str:
    """A signed link straight into BetterMesh, already logged in as this
    hospice's account — see app/sso.py for the signature BetterMesh checks."""
    params = {"hospice": slug, "sig": sso.sign(slug), "next": next_path}
    return f"{_bettermesh_origin(request)}/sso?{urlencode(params)}"


@router.get("/", response_class=HTMLResponse)
def patient_list(request: Request):
    slug = _resolve_hospice_slug(request)
    hospice = HOSPICES[slug]
    return templates.TemplateResponse(
        "care_platform/list.html",
        {
            "request": request,
            "hospice": hospice,
            "patients": patients_for(slug),
            "hospice_qs": f"?hospice={slug}" if request.query_params.get("hospice") else "",
            "bettermesh_url": _bettermesh_sso_url(request, slug, "/"),
            "recent_notifications": list(reversed(_RECENT_NOTIFICATIONS.get(slug, []))),
        },
    )


@router.get("/patients/{patient_id}", response_class=HTMLResponse)
def patient_record(patient_id: str, request: Request):
    slug = _resolve_hospice_slug(request)
    hospice = HOSPICES[slug]
    patient = PATIENTS.get(patient_id.upper())
    qs = f"?hospice={slug}" if request.query_params.get("hospice") else ""

    if patient is None or patient.hospice_slug != slug:
        return templates.TemplateResponse(
            "care_platform/not_found.html", {"request": request, "hospice": hospice, "hospice_qs": qs}, status_code=404
        )

    status_url = _bettermesh_sso_url(request, slug, f"/?{urlencode({'patient': patient.id})}")
    pending_needs = [
        {"code": n.code, "name": n.name, "urgent": n.urgent}
        for n in patient.equipment_needs
        if not n.dispatched
    ]
    return templates.TemplateResponse(
        "care_platform/patient.html",
        {
            "request": request,
            "hospice": hospice,
            "patient": patient,
            "pending_needs": pending_needs,
            "equipment_options": EQUIPMENT,
            "default_target": default_target_date(),
            "default_target_stat": default_target_date("STAT"),
            "status_url": status_url,
            "api_base": _bettermesh_origin(request),
            "webhook_secret": _webhook_secret(),
            "hospice_qs": qs,
        },
    )


@router.post("/webhook/status-update")
async def status_update(request: Request):
    """Receive a push notification from BetterMesh about an order status change.

    This is the other half of app/notifications.py: BetterMesh calls this
    (fire-and-forget, best-effort) whenever a vendor accepts, delivers, or
    completes a pickup, so this hospice's own system doesn't have to keep
    polling GET /api/patients/{id}/orders to find out. Unlike the other
    /webhook/* and /api/* endpoints in this app, this one is receiving a call
    FROM BetterMesh's own server rather than from an arbitrary hospice, so it
    intentionally skips the shared-secret check.
    """
    slug = _resolve_hospice_slug(request)
    try:
        body = await request.json()
    except Exception:
        body = {}

    entry = {
        "order_id": body.get("order_id"),
        "patient_id": body.get("patient_id"),
        "event": body.get("event"),
        "status": body.get("status"),
        "vendor": body.get("vendor"),
        "timestamp": body.get("timestamp"),
    }
    bucket = _RECENT_NOTIFICATIONS.setdefault(slug, [])
    bucket.append(entry)
    _RECENT_NOTIFICATIONS[slug] = bucket[-10:]
    return JSONResponse({"received": True})
