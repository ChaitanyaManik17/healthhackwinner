"""Strict, dependency-free validation of the Call Bell Router ticket contract.

Usage: python -m ai.validate_ticket path/to/ticket.json
       cat ticket.json | python -m ai.validate_ticket -

Invalid model output must be caught by the caller and routed to the nurse. This
module deliberately reports errors without repairing or extracting model JSON.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import datetime
import json
import math
from pathlib import Path
import re
import sys
from typing import Any


TICKET_FIELDS = frozenset({
    "ticket_id", "room", "raw_text", "language", "category", "department",
    "priority", "confidence", "escalate_to_nurse", "reason", "status", "created_at",
})
IMMUTABLE_METADATA_FIELDS = frozenset({
    "ticket_id", "room", "raw_text", "language", "status", "created_at",
})
ROUTES = {
    "housekeeping": ("housekeeping", "normal", False),
    "food": ("food", "normal", False),
    "tech": ("unit_clerk_it", "low", False),
    "urgent_clinical": ("nurse", "high", True),
    "unclear": ("nurse", "high", True),
}
ENUMS = {
    "category": frozenset(ROUTES),
    "department": frozenset({"housekeeping", "food", "unit_clerk_it", "nurse"}),
    "priority": frozenset({"low", "normal", "high"}),
    "status": frozenset({"new", "acknowledged", "done"}),
}
_UTC_TIMESTAMP = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt]"
    r"([0-9]{2}):([0-9]{2}):([0-5][0-9])(?:\.[0-9]+)?(?:[Zz]|\+00:00)"
)


class TicketValidationError(ValueError):
    """The ticket cannot be trusted; its caller must use the nurse fallback."""

    def __init__(self, errors: str | list[str] | tuple[str, ...]):
        self.errors = (errors,) if isinstance(errors, str) else tuple(errors)
        super().__init__("; ".join(self.errors))


def _valid_utc_timestamp(value: str) -> bool:
    match = _UTC_TIMESTAMP.fullmatch(value)
    if match is None:
        return False
    try:
        datetime(*(int(part) for part in match.groups()))
    except ValueError:
        return False
    return True


def enforce_immutable_metadata(
    ticket: Mapping[str, Any], expected_metadata: Mapping[str, Any] | None = None,
) -> None:
    """Reject changes to caller-owned identifiers, request text, and metadata.

    Supply only the metadata the caller already knows. For example, include
    language when the patient supplied it; include status="new" for new tickets.
    Comparison is exact, preserving the original request without normalization.
    """
    if expected_metadata is None:
        return
    if not isinstance(expected_metadata, Mapping):
        raise TicketValidationError("expected_metadata must be a mapping")
    errors = []
    for field, expected in expected_metadata.items():
        if field not in IMMUTABLE_METADATA_FIELDS:
            errors.append("expected_metadata contains an unsupported field")
        elif field not in ticket or type(ticket[field]) is not type(expected) or ticket[field] != expected:
            errors.append(f"{field} differs from caller-owned metadata")
    if errors:
        raise TicketValidationError(errors)


def validate_ticket(
    ticket: Any, expected_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a parsed ticket, returning it unchanged or raising an error.

    This implements ticket.schema.json plus actual calendar-date validation.
    The schema's date-time format should also be asserted by other consumers.
    """
    if not isinstance(ticket, dict):
        raise TicketValidationError("ticket must be a JSON object")
    keys = set(ticket)
    errors = []
    missing = TICKET_FIELDS - keys
    if missing:
        errors.append("missing required fields: " + ", ".join(sorted(missing)))
    if keys - TICKET_FIELDS:
        errors.append("ticket contains additional fields")

    for field in ("ticket_id", "room", "language", "reason"):
        if field in ticket and (not isinstance(ticket[field], str) or not ticket[field].strip()):
            errors.append(f"{field} must be a nonempty string")
    if "raw_text" in ticket and not isinstance(ticket["raw_text"], str):
        errors.append("raw_text must be a string")
    for field, allowed in ENUMS.items():
        value = ticket.get(field)
        if field in ticket and (not isinstance(value, str) or value not in allowed):
            errors.append(f"{field} must be one of: " + ", ".join(sorted(allowed)))

    if "confidence" in ticket:
        confidence = ticket["confidence"]
        if type(confidence) not in (int, float) or not 0 <= confidence <= 1 or not math.isfinite(confidence):
            errors.append("confidence must be a finite number between 0 and 1")
    if "escalate_to_nurse" in ticket and type(ticket["escalate_to_nurse"]) is not bool:
        errors.append("escalate_to_nurse must be a boolean")
    if "created_at" in ticket:
        timestamp = ticket["created_at"]
        if not isinstance(timestamp, str) or not _valid_utc_timestamp(timestamp):
            errors.append("created_at must be a valid RFC 3339 UTC timestamp (Z or +00:00)")

    category = ticket.get("category")
    if isinstance(category, str) and category in ROUTES:
        expected_route = ROUTES[category]
        for field, expected in zip(("department", "priority", "escalate_to_nurse"), expected_route):
            if field in ticket and (type(ticket[field]) is not type(expected) or ticket[field] != expected):
                errors.append(f"{field} does not match the required route for {category}")
    if errors:
        raise TicketValidationError(errors)
    enforce_immutable_metadata(ticket, expected_metadata)
    return ticket


def _reject_nonfinite_constant(value: str) -> None:
    raise TicketValidationError("JSON must not contain NaN or Infinity")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TicketValidationError("JSON must not contain duplicate object keys")
        result[key] = value
    return result


def parse_ticket_json(
    text: str | bytes | bytearray, expected_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse exactly one JSON object, rejecting wrappers and ambiguous JSON."""
    if not isinstance(text, (str, bytes, bytearray)):
        raise TicketValidationError("model output must be JSON text")
    try:
        if isinstance(text, (bytes, bytearray)):
            text = text.decode("utf-8")
        ticket = json.loads(
            text, object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite_constant,
        )
    except TicketValidationError:
        raise
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise TicketValidationError("output is not a single valid JSON object") from exc
    return validate_ticket(ticket, expected_metadata)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Call Bell Router ticket JSON file.")
    parser.add_argument("file", help="JSON file path, or - to read standard input")
    args = parser.parse_args(argv)
    try:
        payload = sys.stdin.buffer.read() if args.file == "-" else Path(args.file).read_bytes()
        parse_ticket_json(payload)
    except (OSError, TicketValidationError) as exc:
        print(f"Invalid ticket: {exc}", file=sys.stderr)
        return 1
    print("Valid ticket JSON.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
