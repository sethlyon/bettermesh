"""Self-hosted QR codes for the running demo pages.

Generated locally (SVG, no Pillow) and inlined as a data URI — no external
QR-generation API, matching the app's "no external calls" posture.
"""
from __future__ import annotations

import base64
from functools import lru_cache
from io import BytesIO

import qrcode
import qrcode.image.svg
from starlette.requests import Request


@lru_cache(maxsize=64)
def _svg_data_uri(url: str) -> str:
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
    buf = BytesIO()
    img.save(buf)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def public_url(request: Request) -> str:
    """Absolute, browser-facing URL for this request (current path + query).

    Behind the Cloudflare Worker, every hospice site is a distinct real HTTPS
    domain, but the app only reliably sees the original Host header, not
    always the original scheme — so force https for anything that isn't the
    local dev host, same approach as care_platform._bettermesh_origin.
    """
    host = (request.headers.get("host") or "").split(":")[0]
    scheme = "http" if host in ("127.0.0.1", "localhost") else "https"
    query = f"?{request.url.query}" if request.url.query else ""
    return f"{scheme}://{request.headers.get('host')}{request.url.path}{query}"


def qr_for_request(request: Request) -> str:
    return _svg_data_uri(public_url(request))
