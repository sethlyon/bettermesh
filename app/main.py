"""BetterMesh by BetterRX - hackathon MVP.

FastAPI + HTMX single app with two role views over one shared order board.
Run: uvicorn app.main:app --reload  (from the bettermesh/ directory)
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from typing import Optional
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import auth, dispatch, store
from .care_platform import router as care_platform_router
from .models import (
    ACTIVE_DELIVERY_STATES,
    EQUIPMENT,
    ORDERED,
    PICKUP_REQUESTED,
    Order,
)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="BetterMesh by BetterRX")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(care_platform_router)

# Session cookie is signed with this key. Set SESSION_SECRET in the
# environment for anything beyond local demo use (see .env.example).
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-insecure-secret-change-me")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# The care-platform mock hospice sites (care_platform.py) live on separate
# subdomains and call the /webhook/* and /api/* endpoints below via browser
# fetch() — without CORS those cross-origin calls are blocked by the browser
# even though a plain curl/server-to-server call never hits this at all,
# which is exactly why this gap survived earlier curl-only testing.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://anchorpoint.theslyon.com",
        "https://cedarridge.theslyon.com",
        "https://thistlemoor.theslyon.com",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Webhook-Secret"],
)

# Seed at import so the board is populated however the app is launched.
store.seed()


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%-I:%M %p") if dt else "—"


templates.env.filters["t"] = _fmt


def _current_user(request: Request) -> auth.User | None:
    """Resolve the logged-in user from the signed session cookie, if any."""
    username = request.session.get("username")
    if not username:
        return None
    return auth.get_user(username)


def _login_required_response() -> HTMLResponse:
    """For htmx action routes hit without a valid session: htmx will follow
    the HX-Redirect header and do a full-page navigation to /login."""
    resp = HTMLResponse("Session expired — please log in again.", status_code=401)
    resp.headers["HX-Redirect"] = "/login"
    return resp


def _board_ctx(request: Request, user: auth.User, flash: str = "", highlight_patient: str = "") -> dict:
    orders = store.all_orders()
    ctx: dict = {
        "request": request,
        "role": user.role,
        "user": user,
        "orders": orders,
        "flash": flash,
        "highlight_patient": highlight_patient,
        "equipment": EQUIPMENT,
    }

    if user.role == "hospice":
        ctx["recommendations"] = {
            o.id: dispatch.best_candidate_for(o) for o in orders if o.at_risk or o.is_open
        }

    if user.role == "dispatcher":
        vendor = user.vendor
        ctx["vendor"] = vendor
        ctx["opportunities"] = dispatch.opportunities_for(vendor, orders)
        ctx["my_deliveries"] = [
            o
            for o in orders
            if o.vendor == vendor and not o.is_pickup and o.status in ACTIVE_DELIVERY_STATES
        ]
        ctx["pickups"] = [
            o
            for o in orders
            if o.vendor == vendor and o.is_pickup and o.status == PICKUP_REQUESTED
        ]
    return ctx


def _safe_next(next_path: str | None) -> str:
    """Only ever redirect to a path on this same site (never an open redirect)."""
    if next_path and next_path.startswith("/") and not next_path.startswith("//"):
        return next_path
    return "/"


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, next: Optional[str] = None):
    safe_next = _safe_next(next)
    if _current_user(request) is not None:
        return RedirectResponse(safe_next, status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "", "next": safe_next})


@app.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    safe_next = _safe_next(next)
    user = auth.verify_login(username.strip(), password)
    if user is None:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password.", "next": safe_next},
            status_code=401,
        )
    request.session.clear()
    request.session["username"] = user.username
    return RedirectResponse(safe_next, status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
def index(request: Request, patient: Optional[str] = None):
    user = _current_user(request)
    if user is None:
        next_path = "/" + (f"?{urlencode({'patient': patient})}" if patient else "")
        return RedirectResponse(f"/login?{urlencode({'next': next_path})}", status_code=303)
    return templates.TemplateResponse(
        "board.html", _board_ctx(request, user, highlight_patient=(patient or "").strip().upper())
    )


@app.get("/dispatches", response_class=HTMLResponse)
def all_dispatches(
    request: Request,
    patient_id: str = "",
    equipment_code: list[str] = Query(default=[]),
):
    """Flat, filterable view of every DME dispatch and pickup — a companion to
    the kanban board, which groups by status/attention rather than letting a
    hospice browse or filter its full order history directly."""
    user = _current_user(request)
    if user is None:
        return RedirectResponse(f"/login?{urlencode({'next': str(request.url.path)})}", status_code=303)
    if user.role != "hospice":
        return RedirectResponse("/", status_code=303)

    all_orders = store.all_orders()
    orders = all_orders
    if patient_id:
        orders = [o for o in orders if o.patient_id == patient_id]
    if equipment_code:
        orders = [o for o in orders if o.equipment_code in equipment_code]
    orders = sorted(orders, key=lambda o: o.ordered_at, reverse=True)

    patient_ids = sorted({o.patient_id for o in all_orders})
    return templates.TemplateResponse(
        "dispatches.html",
        {
            "request": request,
            "user": user,
            "orders": orders,
            "patient_ids": patient_ids,
            "equipment": EQUIPMENT,
            "selected_patient": patient_id,
            "selected_equipment": equipment_code,
        },
    )


@app.post("/orders/{order_id}/rebroadcast", response_class=HTMLResponse)
def rebroadcast(request: Request, order_id: str):
    user = _current_user(request)
    if user is None:
        return _login_required_response()
    order = store.get(order_id)
    flash = "Order not found."
    if order:
        _, flash = dispatch.rebroadcast(order)
    return templates.TemplateResponse("_board_inner.html", _board_ctx(request, user, flash))


@app.post("/orders/{order_id}/accept", response_class=HTMLResponse)
def accept(request: Request, order_id: str):
    user = _current_user(request)
    if user is None:
        return _login_required_response()
    order = store.get(order_id)
    if user.role != "dispatcher" or not user.vendor:
        flash = "Only a dispatcher account can accept orders."
    else:
        flash = "Order not found."
        if order:
            _, flash = dispatch.accept(order, user.vendor)
    return templates.TemplateResponse("_board_inner.html", _board_ctx(request, user, flash))


@app.post("/orders/{order_id}/deliver", response_class=HTMLResponse)
def deliver(request: Request, order_id: str):
    user = _current_user(request)
    if user is None:
        return _login_required_response()
    order = store.get(order_id)
    if user.role != "dispatcher":
        flash = "Only a dispatcher account can mark a delivery complete."
    elif not order or order.vendor != user.vendor:
        flash = "Order not found."
    else:
        _, flash = dispatch.mark_delivered(order)
    return templates.TemplateResponse("_board_inner.html", _board_ctx(request, user, flash))


@app.post("/orders/{order_id}/pickup-complete", response_class=HTMLResponse)
def pickup_complete(request: Request, order_id: str):
    user = _current_user(request)
    if user is None:
        return _login_required_response()
    order = store.get(order_id)
    if user.role != "dispatcher":
        flash = "Only a dispatcher account can confirm a pickup."
    elif not order or order.vendor != user.vendor:
        flash = "Order not found."
    else:
        _, flash = dispatch.complete_pickup(order)
    return templates.TemplateResponse("_board_inner.html", _board_ctx(request, user, flash))


@app.post("/patients/deceased", response_class=HTMLResponse)
def deceased(request: Request, patient_id: str = Form(...)):
    user = _current_user(request)
    if user is None:
        return _login_required_response()
    count, ids = dispatch.mark_deceased(patient_id.strip().upper())
    if count:
        flash = f"Pickup requested for {patient_id.upper()} ({', '.join(ids)})."
    else:
        flash = f"No delivered equipment found for {patient_id.upper()}."
    return templates.TemplateResponse("_board_inner.html", _board_ctx(request, user, flash))


@app.post("/orders", response_class=HTMLResponse)
def create_order(
    request: Request,
    equipment_code: str = Form(...),
    patient_id: str = Form(...),
    target_date: str = Form(...),
    address: str = Form(""),
):
    user = _current_user(request)
    if user is None:
        return _login_required_response()

    patient_id = patient_id.strip().upper()
    target: datetime | None
    try:
        target = datetime.fromisoformat(target_date) if target_date else None
    except ValueError:
        target = None

    if equipment_code not in EQUIPMENT or not patient_id or target is None:
        flash = "Choose an equipment type, enter a patient ID, and set a target date/time."
        return templates.TemplateResponse("_board_inner.html", _board_ctx(request, user, flash))

    order = Order(
        id=store.next_id(),
        patient_id=patient_id,
        hospice="Anchorpoint Hospice Partners",
        equipment_code=equipment_code,
        order_type="Admission",
        status=ORDERED,
        ordered_at=datetime.now(),
        target_date=target,
        address=address.strip(),
    )
    order.log.append("manual fallback entry — not yet on a discharge record")
    store.add(order)
    flash = f"Created {order.id}: {order.equipment_name} for {order.patient_id} — now open to the network."
    return templates.TemplateResponse("_board_inner.html", _board_ctx(request, user, flash))


def _webhook_authorized(request: Request) -> bool:
    """Shared-secret check for the system-to-system API surface (webhook + read
    API). Not a real auth scheme — a stand-in for whatever a hospice's system
    and BetterMesh would actually negotiate (mTLS, OAuth client credentials,
    etc.) in production. Demo-appropriate, not production-appropriate."""
    secret = os.environ.get("WEBHOOK_SECRET", "dev-insecure-webhook-secret-change-me")
    return request.headers.get("x-webhook-secret") == secret


def _order_json(o: Order) -> dict:
    return {
        "id": o.id,
        "equipment_code": o.equipment_code,
        "equipment_name": o.equipment_name,
        "order_type": o.order_type,
        "status": o.status,
        "vendor": o.vendor,
        "target_date": o.target_date.isoformat() if o.target_date else None,
        "eta": o.eta.isoformat() if o.eta else None,
        "at_risk": o.at_risk,
        "is_pickup": o.is_pickup,
        "address": o.address,
        "contact_phone": o.contact_phone,
        "equipment_notes": o.equipment_notes,
    }


@app.get("/api/patients/{patient_id}/orders")
def api_patient_orders(patient_id: str, request: Request):
    """Read-side of the system-to-system API: a hospice's own record system

    (see care-platform/) queries this to show live BetterMesh status inline on
    a patient's chart, instead of only ever linking out to the full board.
    """
    if not _webhook_authorized(request):
        return HTMLResponse('{"error": "unauthorized"}', status_code=401, media_type="application/json")

    patient_id = patient_id.strip().upper()
    orders = [_order_json(o) for o in store.all_orders() if o.patient_id == patient_id]
    return {"patient_id": patient_id, "orders": orders}


@app.post("/webhook/pre-discharge-order")
async def webhook_pre_discharge_order(request: Request):
    """Unauthenticated system-to-system intake: a hospice's own record system

    (see care-platform/) pushes an already-structured DME need straight in, the
    way the pitch describes BetterRX's discharge record integration working — no
    parsing, no login, just a shared secret proving the caller is trusted.
    """
    if not _webhook_authorized(request):
        return HTMLResponse('{"error": "unauthorized"}', status_code=401, media_type="application/json")

    body = await request.json()
    patient_id = str(body.get("patient_id", "")).strip().upper()
    hospice = str(body.get("hospice", "")).strip()
    order_type = str(body.get("order_type", "Admission")).strip() or "Admission"
    equipment_codes = body.get("equipment_codes") or []
    address = str(body.get("address", "")).strip()
    contact_phone = str(body.get("contact_phone", "")).strip()
    equipment_notes = str(body.get("equipment_notes", "")).strip()
    try:
        target = datetime.fromisoformat(body["target_date"]) if body.get("target_date") else None
    except (ValueError, KeyError):
        target = None

    if not patient_id or not hospice or not equipment_codes or target is None:
        return HTMLResponse(
            '{"error": "patient_id, hospice, equipment_codes, and target_date are required"}',
            status_code=400,
            media_type="application/json",
        )
    if not address:
        return HTMLResponse(
            '{"error": "address is required — a DME vendor cannot fulfill an order without a delivery address"}',
            status_code=400,
            media_type="application/json",
        )

    created: list[str] = []
    for code in equipment_codes:
        if code not in EQUIPMENT:
            continue
        order = Order(
            id=store.next_id(),
            patient_id=patient_id,
            hospice=hospice,
            equipment_code=code,
            order_type=order_type,
            status=ORDERED,
            ordered_at=datetime.now(),
            target_date=target,
            address=address,
            contact_phone=contact_phone,
            equipment_notes=equipment_notes,
        )
        order.log.append(f"received via pre-discharge webhook from {hospice}")
        store.add(order)
        created.append(order.id)

    if not created:
        return HTMLResponse('{"error": "no valid equipment_codes"}', status_code=400, media_type="application/json")

    return {"created": created, "patient_id": patient_id}


@app.post("/webhook/mark-deceased")
async def webhook_mark_deceased(request: Request):
    """System-to-system version of the hospice-side 'Mark deceased' action —

    same underlying dispatch.mark_deceased() logic the logged-in hospice board
    uses, exposed so a hospice's own record system (see care-platform/) can
    trigger it directly when a patient's status is updated there, instead of
    someone re-entering it a second time in BetterMesh.
    """
    if not _webhook_authorized(request):
        return HTMLResponse('{"error": "unauthorized"}', status_code=401, media_type="application/json")

    body = await request.json()
    patient_id = str(body.get("patient_id", "")).strip().upper()
    if not patient_id:
        return HTMLResponse('{"error": "patient_id is required"}', status_code=400, media_type="application/json")

    count, ids = dispatch.mark_deceased(patient_id)
    pickups = [_order_json(store.get(i)) for i in ids]
    return {"patient_id": patient_id, "pickup_count": count, "pickups": pickups}


@app.post("/reset", response_class=HTMLResponse)
def reset(request: Request):
    user = _current_user(request)
    if user is None:
        return _login_required_response()
    store.seed()
    return templates.TemplateResponse(
        "_board_inner.html", _board_ctx(request, user, "Demo data reset.")
    )
