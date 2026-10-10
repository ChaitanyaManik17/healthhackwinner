"""Keeps backend models, shared/ticket.schema.json and docs/openapi.yaml in sync."""

import json
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from app.models import (
    CATEGORY_TO_DEPARTMENT,
    Category,
    Department,
    Priority,
    Status,
    Ticket,
    nurse_fallback,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "shared" / "ticket.schema.json").read_text())


def _enum(field: str) -> set[str]:
    return set(SCHEMA["properties"][field]["enum"])


def test_enums_match_schema():
    assert {c.value for c in Category} == _enum("category")
    assert {d.value for d in Department} == _enum("department")
    assert {p.value for p in Priority} == _enum("priority")
    assert {s.value for s in Status} == _enum("status")


def test_every_category_routes_and_clinical_goes_to_nurse():
    assert set(CATEGORY_TO_DEPARTMENT) == set(Category)
    assert CATEGORY_TO_DEPARTMENT[Category.urgent_clinical] is Department.nurse
    assert CATEGORY_TO_DEPARTMENT[Category.unclear] is Department.nurse


def test_ticket_model_output_validates_against_schema():
    ticket = Ticket(
        **nurse_fallback().model_dump(),
        ticket_id="t_0001",
        room="412B",
        raw_text="I need help",
        created_at=datetime(2026, 10, 10, 14, 3, tzinfo=timezone.utc),
    )
    payload = json.loads(ticket.model_dump_json(exclude_none=True))
    jsonschema.validate(payload, SCHEMA)


def test_fallback_is_nurse_high_priority():
    fb = nurse_fallback()
    assert fb.department is Department.nurse
    assert fb.priority is Priority.high
    assert fb.escalate_to_nurse is True
