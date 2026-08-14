"""Hardcoded demo account table + password hashing for BetterMesh.

This is a hackathon demo, not a real user-management system: accounts live in
a small in-memory table instead of a database. Passwords are still stored as
salted SHA-256 hashes rather than plaintext, and login is a real
username/password check against those hashes.

One unrestricted hospice case-manager account (sees every hospice's orders),
plus one tenant-scoped account per hospice brand (`hospice` set to that
brand's exact `Order.hospice` string, so it only ever sees and acts on its
own hospice's orders) and one dispatcher account per entry in `VENDORS`
(models.py) so each vendor's dispatcher can only ever see and act on that
vendor's own board.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

from .models import VENDORS

HOSPICE = "hospice"
DISPATCHER = "dispatcher"


@dataclass(frozen=True)
class User:
    username: str
    role: str  # "hospice" | "dispatcher"
    vendor: str | None  # set only for dispatcher accounts
    display_name: str
    hospice: str | None = None  # set only for tenant-scoped hospice accounts


def _hash_password(password: str, salt: str) -> str:
    """Salted SHA-256. Good enough for a demo fixed account table; a real
    deployment would use a slow KDF (bcrypt/scrypt/argon2) instead."""
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def _account(
    username: str,
    password: str,
    role: str,
    *,
    vendor: str | None = None,
    hospice: str | None = None,
    display_name: str | None = None,
) -> dict:
    salt = username
    return {
        "username": username,
        "password_hash": _hash_password(password, salt),
        "salt": salt,
        "role": role,
        "vendor": vendor,
        "hospice": hospice,
        "display_name": display_name or username,
    }


# --- Demo account table -----------------------------------------------
# Plaintext passwords only ever exist here, at import time, to be hashed.
_ACCOUNTS: list[dict] = [
    _account(
        "casemanager",
        "hospice123",
        HOSPICE,
        hospice=None,  # no tenant restriction — sees every hospice's orders
        display_name="Hospice Case Manager",
    ),
    _account(
        "anchorpoint",
        "anchorpoint123",
        HOSPICE,
        hospice="Anchorpoint Hospice Partners",
        display_name="Anchorpoint Case Manager",
    ),
    _account(
        "cedarridge",
        "cedarridge123",
        HOSPICE,
        hospice="Cedar Ridge Hospice & Home Care",
        display_name="Cedar Ridge Case Manager",
    ),
    _account(
        "thistlemoor",
        "thistlemoor123",
        HOSPICE,
        hospice="Thistlemoor Hospice",
        display_name="Thistlemoor Case Manager",
    ),
    *[
        _account(
            f"dispatcher{i}",
            f"vendor{i}pass",
            DISPATCHER,
            vendor=name,
            display_name=f"{name} Dispatcher",
        )
        for i, name in enumerate(VENDORS.keys(), start=1)
    ],
]

USERS: dict[str, dict] = {a["username"]: a for a in _ACCOUNTS}


def get_user(username: str) -> User | None:
    """Look up a user by username only (used to rehydrate a session)."""
    account = USERS.get(username)
    if account is None:
        return None
    return User(
        username=account["username"],
        role=account["role"],
        vendor=account["vendor"],
        display_name=account["display_name"],
        hospice=account["hospice"],
    )


def verify_login(username: str, password: str) -> User | None:
    """Check a username/password pair; returns the User on success."""
    account = USERS.get(username)
    if account is None:
        return None
    candidate = _hash_password(password, account["salt"])
    if not hmac.compare_digest(candidate, account["password_hash"]):
        return None
    return get_user(username)
