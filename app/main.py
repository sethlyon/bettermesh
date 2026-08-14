"""BetterMesh by BetterRX - hackathon MVP.

FastAPI + HTMX single app with two role views over one shared order board.
Run: uvicorn app.main:app --reload  (from the bettermesh/ directory)
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import auth, dispatch, store
from .models import (
    ACTIVE_DELIVERY_STATES,
    ORDERED,
    PICKUP_REQUESTED,
    Order,
)
from .nlp import parse_order

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="BetterMesh by BetterRX")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Session cookie is signed with this key. Set SESSION_SECRET in the
# environment for anything beyond local demo use (see .env.example).
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-insecure-secret-change-me")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

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


def _board_ctx(request: Request, user: auth.User, flash: str = "") -> dict:
    orders = store.all_orders()
    ctx: dict = {"request": request, "role": user.role, "user": user, "orders": orders, "flash": flash}

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


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if _current_user(request) is not None:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})


@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    user = auth.verify_login(username.strip(), password)
    if user is None:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password."},
            status_code=401,
        )
    request.session.clear()
    request.session["username"] = user.username
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    user = _current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("board.html", _board_ctx(request, user))


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
def create_order(request: Request, text: str = Form(...)):
    user = _current_user(request)
    if user is None:
        return _login_required_response()
    draft = parse_order(text)
    if not draft["equipment_code"] or not draft["patient_id"]:
        flash = "Could not parse equipment or patient. Try: 'hospital bed for PT-88421 by tomorrow 2pm'."
        return templates.TemplateResponse("_board_inner.html", _board_ctx(request, user, flash))

    order = Order(
        id=store.next_id(),
        patient_id=draft["patient_id"],
        hospice="Sample Hospice A",
        equipment_code=draft["equipment_code"],
        order_type=draft["order_type"],
        status=ORDERED,
        ordered_at=datetime.now(),
        target_date=draft["target_date"],
    )
    order.log.append(f'parsed from: "{text}"')
    store.add(order)
    flash = f"Created {order.id}: {order.equipment_name} for {order.patient_id} — now open to the network."
    return templates.TemplateResponse("_board_inner.html", _board_ctx(request, user, flash))


@app.post("/reset", response_class=HTMLResponse)
def reset(request: Request):
    user = _current_user(request)
    if user is None:
        return _login_required_response()
    store.seed()
    return templates.TemplateResponse(
        "_board_inner.html", _board_ctx(request, user, "Demo data reset.")
    )
