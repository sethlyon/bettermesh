"""Outbound push notifications: BetterMesh -> hospice back-office system.

Today the data flow into BetterMesh is one-way (hospice pushes orders in via
/webhook/pre-discharge-order and /webhook/mark-deceased) and the hospice can
only learn what happened by polling GET /api/patients/{id}/orders. This module
adds the other direction: a best-effort push back to the hospice's own system
whenever something changes on BetterMesh's side (accepted, delivered, pickup
completed).

This is explicitly fire-and-forget. A hospice endpoint that is slow, down, or
misconfigured must never slow down or break the vendor/dispatcher action that
triggered the notification - that's why every failure mode here is swallowed
and merely logged to stderr.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime
from typing import Any

# Display name (Order.hospice) -> the hospice's own status-update webhook URL,
# reached in production via that hospice's own subdomain.
_HOSPICE_NOTIFICATION_URLS: dict[str, str] = {
    "Anchorpoint Hospice Partners": "https://anchorpoint.theslyon.com/care-platform/webhook/status-update",
    "Cedar Ridge Hospice & Home Care": "https://cedarridge.theslyon.com/care-platform/webhook/status-update",
    "Thistlemoor Hospice": "https://thistlemoor.theslyon.com/care-platform/webhook/status-update",
}

# Display name (Order.hospice) -> hospice slug, for local testing where there's
# no real subdomain routing and everything shares one origin (127.0.0.1:8000).
_HOSPICE_NAME_TO_SLUG: dict[str, str] = {
    "Anchorpoint Hospice Partners": "anchorpoint",
    "Cedar Ridge Hospice & Home Care": "cedarridge",
    "Thistlemoor Hospice": "thistlemoor",
}


def _target_url(hospice_name: str) -> str | None:
    local_base = os.environ.get("NOTIFICATIONS_LOCAL_BASE")
    if local_base:
        slug = _HOSPICE_NAME_TO_SLUG.get(hospice_name)
        if slug is None:
            return None
        return f"{local_base.rstrip('/')}/care-platform/webhook/status-update?hospice={slug}"
    return _HOSPICE_NOTIFICATION_URLS.get(hospice_name)


def notify_hospice(order: Any, event: str) -> None:
    """Best-effort push of an order status change back to the hospice's system.

    Never raises: any lookup, network, or serialization failure is caught and
    logged to stderr, so a dead or slow hospice endpoint can never break or
    delay the BetterMesh action (accept/deliver/pickup) that triggered it.
    """
    try:
        url = _target_url(order.hospice)
        if not url:
            print(
                f"notify_hospice: no notification URL for hospice "
                f"{order.hospice!r}; skipping ({event} on {order.id})",
                file=sys.stderr,
            )
            return

        payload = {
            "order_id": order.id,
            "patient_id": order.patient_id,
            "event": event,
            "status": order.status,
            "vendor": order.vendor,
            "timestamp": datetime.now().isoformat(),
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=3)
    except Exception as exc:  # noqa: BLE001 - intentionally broad; must never propagate
        print(
            f"notify_hospice: failed to notify for order "
            f"{getattr(order, 'id', '?')} event={event!r}: {exc}",
            file=sys.stderr,
        )
