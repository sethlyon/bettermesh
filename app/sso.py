"""Signed hand-off from a hospice's care-platform site into BetterMesh.

Reuses the same shared-secret trust boundary as the webhook API
(_webhook_authorized in main.py, WEBHOOK_SECRET): the hospice's own system
and BetterMesh already negotiate one secret out-of-band in this demo's
fiction. A link out of care-platform to BetterMesh is signed with it, so
BetterMesh can log the visitor straight into that hospice's account instead
of showing a credential form — the browser never sees WEBHOOK_SECRET itself
(unlike the demo's in-page webhook fetch calls), so it can't forge a
signature for a hospice it didn't come from.
"""
from __future__ import annotations

import hashlib
import hmac
import os


def _secret() -> str:
    return os.environ.get("WEBHOOK_SECRET", "dev-insecure-webhook-secret-change-me")


def sign(hospice_slug: str) -> str:
    return hmac.new(_secret().encode("utf-8"), hospice_slug.encode("utf-8"), hashlib.sha256).hexdigest()


def verify(hospice_slug: str, signature: str) -> bool:
    return hmac.compare_digest(sign(hospice_slug), signature)
