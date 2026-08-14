"""Natural-language order intake.

Calls Claude (via the `anthropic` Python SDK) to parse free-text equipment
orders into structured fields, using tool use so the response is guaranteed
structured JSON rather than free text we'd have to regex apart.

Graceful degradation: if ANTHROPIC_API_KEY isn't set, or the API call fails
for any reason, this returns a draft with every field set to None. The
caller (main.py's create_order route) already treats an unparsed draft as
a "could not parse, please retry" case, so a missing key or a flaky API
call degrades to a flash message instead of a 500.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv

    # Support a .env at the ai-builder-day repo root (two levels above this
    # package: bettermesh/app/nlp.py -> bettermesh/ -> repo root) in addition
    # to the current working directory, so `ANTHROPIC_API_KEY=...` dropped
    # in the repo root's .env is picked up regardless of where uvicorn runs.
    _repo_root_env = Path(__file__).resolve().parents[2] / ".env"
    if _repo_root_env.exists():
        load_dotenv(_repo_root_env)
    load_dotenv()
except ImportError:  # pragma: no cover - python-dotenv is a soft dependency
    pass

MODEL = "claude-sonnet-5"

# Sentinel the model uses to say "not mentioned" for a required field, since
# plain JSON schema (without nullable types) can't express "string or null"
# uniformly across tool-use implementations. We translate it to None below.
_NOT_MENTIONED = "NONE"

_EMPTY_DRAFT: dict = {
    "equipment_code": None,
    "patient_id": None,
    "order_type": None,
    "target_date": None,
}

_VALID_EQUIPMENT_CODES = {"E0250", "E1130", "E0601"}

_RECORD_ORDER_DRAFT_TOOL = {
    "name": "record_order_draft",
    "description": (
        "Record the structured fields extracted from a free-text durable "
        "medical equipment order for a hospice patient."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "equipment_code": {
                "type": "string",
                "enum": ["E0250", "E1130", "E0601", _NOT_MENTIONED],
                "description": (
                    "HCPCS equipment code implied by the text: E0250 = "
                    "Hospital Bed, E1130 = Wheelchair, E0601 = CPAP / Oxygen "
                    f"Concentrator. Use '{_NOT_MENTIONED}' if no equipment is "
                    "mentioned or it doesn't clearly match one of these three."
                ),
            },
            "patient_id": {
                "type": "string",
                "description": (
                    "Patient identifier token such as 'PT-88421', uppercased "
                    f"exactly as written. Use '{_NOT_MENTIONED}' if no "
                    "patient identifier is mentioned."
                ),
            },
            "order_type": {
                "type": "string",
                "enum": ["STAT", "Admission"],
                "description": (
                    "'STAT' if the text uses urgent language (e.g. 'stat', "
                    "'urgent', 'asap', 'emergency', 'immediately'); "
                    "otherwise 'Admission'."
                ),
            },
            "target_date": {
                "type": "string",
                "description": (
                    "The target date/time, resolved to an absolute ISO 8601 "
                    "timestamp (YYYY-MM-DDTHH:MM:SS) by interpreting any "
                    "relative language ('tomorrow 2pm', 'today', 'by Friday "
                    "9am', etc.) against the current date/time provided in "
                    f"the system prompt. Use '{_NOT_MENTIONED}' if no date "
                    "or time is mentioned at all."
                ),
            },
        },
        "required": ["equipment_code", "patient_id", "order_type", "target_date"],
    },
}


def parse_order(text: str) -> dict:
    """Parse free text into a structured order draft.

    Returns a dict with equipment_code, patient_id, order_type and
    target_date. Unknown fields come back as None so the caller can prompt
    for them. target_date is a datetime (or None), never a string.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "nlp.parse_order: ANTHROPIC_API_KEY is not set; returning an "
            "empty draft instead of calling the LLM.",
            file=sys.stderr,
        )
        return dict(_EMPTY_DRAFT)

    try:
        return _parse_with_llm(text, api_key)
    except Exception as exc:  # noqa: BLE001 - any failure must degrade gracefully
        print(
            f"nlp.parse_order: LLM parse failed ({exc!r}); returning an "
            "empty draft so the caller can prompt the user to retry.",
            file=sys.stderr,
        )
        return dict(_EMPTY_DRAFT)


def _parse_with_llm(text: str, api_key: str) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    now = datetime.now()

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=(
            "You extract structured durable medical equipment order details "
            "from short, free-text hospice equipment orders. Always call "
            "the record_order_draft tool exactly once with your best "
            f"extraction. The current date and time is {now.isoformat()} "
            f"({now.strftime('%A')}); resolve any relative dates or times "
            "in the order text against this."
        ),
        tools=[_RECORD_ORDER_DRAFT_TOOL],
        tool_choice={"type": "tool", "name": "record_order_draft"},
        messages=[{"role": "user", "content": text}],
    )

    tool_use = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )
    if tool_use is None:
        print(
            "nlp.parse_order: model response had no tool_use block; "
            "returning an empty draft.",
            file=sys.stderr,
        )
        return dict(_EMPTY_DRAFT)

    data = tool_use.input if isinstance(tool_use.input, dict) else {}

    equipment_code = data.get("equipment_code")
    if equipment_code not in _VALID_EQUIPMENT_CODES:
        equipment_code = None

    patient_id = data.get("patient_id")
    patient_id = (
        patient_id.strip().upper()
        if isinstance(patient_id, str) and patient_id.strip() and patient_id != _NOT_MENTIONED
        else None
    )

    order_type = data.get("order_type")
    order_type = order_type if order_type in {"STAT", "Admission"} else "Admission"

    target_date = None
    raw_target = data.get("target_date")
    if isinstance(raw_target, str) and raw_target and raw_target != _NOT_MENTIONED:
        try:
            target_date = datetime.fromisoformat(raw_target)
        except ValueError:
            print(
                f"nlp.parse_order: could not parse target_date {raw_target!r} "
                "as ISO 8601; leaving it unset.",
                file=sys.stderr,
            )
            target_date = None

    return {
        "equipment_code": equipment_code,
        "patient_id": patient_id,
        "order_type": order_type,
        "target_date": target_date,
    }
