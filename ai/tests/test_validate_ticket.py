"""Contract boundary tests; no Bedrock access or third-party packages required."""

import json
import math
from pathlib import Path
import unittest

from ai.validate_ticket import (
    TicketValidationError, enforce_immutable_metadata, parse_ticket_json, validate_ticket,
)


def sample_ticket(**changes):
    ticket = {
        "ticket_id": "t_0001", "room": "412B",
        "raw_text": "my incision is throbbing and I feel dizzy", "language": "en",
        "category": "urgent_clinical", "department": "nurse", "priority": "high",
        "confidence": 0.97, "escalate_to_nurse": True,
        "reason": "pain and dizziness near surgical site", "status": "new",
        "created_at": "2026-10-09T14:03:00Z",
    }
    ticket.update(changes)
    return ticket


class TicketValidationTests(unittest.TestCase):
    def assert_invalid(self, ticket):
        with self.assertRaises(TicketValidationError):
            validate_ticket(ticket)

    def test_plan_example_preserved(self):
        ticket = sample_ticket()
        self.assertIs(validate_ticket(ticket), ticket)
        self.assertEqual(parse_ticket_json(json.dumps(ticket)), ticket)

    def test_all_five_routes(self):
        routes = (
            ("housekeeping", "housekeeping", "normal", False),
            ("food", "food", "normal", False),
            ("tech", "unit_clerk_it", "low", False),
            ("urgent_clinical", "nurse", "high", True),
            ("unclear", "nurse", "high", True),
        )
        for category, department, priority, escalate in routes:
            with self.subTest(category=category):
                validate_ticket(sample_ticket(category=category, department=department,
                                              priority=priority, escalate_to_nurse=escalate))

    def test_wrong_department_priority_and_escalation_rejected(self):
        for changes in (
            {"department": "food"}, {"priority": "low"}, {"escalate_to_nurse": False},
            {"category": "housekeeping"}, {"escalate_to_nurse": 1},
            {"category": "tech", "department": "unit_clerk_it", "priority": "normal", "escalate_to_nurse": False},
        ):
            with self.subTest(changes=changes):
                self.assert_invalid(sample_ticket(**changes))

    def test_every_field_required_and_extra_fields_rejected(self):
        for field in sample_ticket():
            with self.subTest(field=field):
                ticket = sample_ticket()
                del ticket[field]
                self.assert_invalid(ticket)
        self.assert_invalid(sample_ticket(hidden_route="food"))

    def test_empty_raw_text_is_valid_for_nurse_fallback(self):
        validate_ticket(sample_ticket(category="unclear", raw_text="", confidence=0))

    def test_nonempty_string_fields_and_raw_text_type(self):
        for field in ("ticket_id", "room", "language", "reason"):
            for value in ("", " \t\n", None, 1, []):
                with self.subTest(field=field, value=value):
                    self.assert_invalid(sample_ticket(**{field: value}))
        self.assert_invalid(sample_ticket(raw_text=None))

    def test_invalid_enums_rejected_without_type_errors(self):
        for field in ("category", "department", "priority", "status"):
            for value in ("invalid", None, [], {}):
                with self.subTest(field=field, value=value):
                    self.assert_invalid(sample_ticket(**{field: value}))

    def test_confidence_must_be_finite_numeric_probability(self):
        for value in (True, False, "0.97", None, -0.01, 1.01, math.nan,
                      math.inf, -math.inf, 10 ** 1000):
            with self.subTest(value=str(value)[:30]):
                self.assert_invalid(sample_ticket(confidence=value))
        for value in (0, 1, 0.0, 1.0):
            validate_ticket(sample_ticket(confidence=value))

    def test_actual_calendar_and_utc_required(self):
        for timestamp in (
            "2026-02-29T14:03:00Z", "2026-02-30T14:03:00Z", "2026-13-09T14:03:00Z",
            "2026-10-00T14:03:00Z", "0000-10-09T14:03:00Z", "2026-10-09T24:03:00Z",
            "2026-10-09T14:60:00Z", "2026-10-09T14:03:60Z", "2026-10-09T14:03:00",
            "2026-10-09 14:03:00Z", "2026-10-09T14:03:00-04:00", "2026-10-09T14:03:00-00:00",
            "2026-10-09T14:03:00+01:00", "2026-10-09T14:03:00.Z", "2026-10-09T14:03:00Z\n",
        ):
            with self.subTest(timestamp=timestamp):
                self.assert_invalid(sample_ticket(created_at=timestamp))
        for timestamp in (
            "2024-02-29T00:00:00Z", "2026-10-09T14:03:00.123456789Z",
            "2026-10-09T14:03:00+00:00", "2026-10-09t14:03:00z",
        ):
            validate_ticket(sample_ticket(created_at=timestamp))

    def test_strict_json_rejects_fences_prefix_suffix_and_nonobjects(self):
        valid = json.dumps(sample_ticket())
        for output in ("```json\n" + valid + "\n```", "Ticket: " + valid,
                       valid + " trailing", valid + valid, "[]", "null", "true", "42", "\"text\""):
            with self.subTest(output=output[:30]):
                with self.assertRaises(TicketValidationError):
                    parse_ticket_json(output)
        self.assertEqual(parse_ticket_json(" \n" + valid + "\t "), sample_ticket())

    def test_duplicate_keys_and_nonfinite_json_rejected(self):
        valid = json.dumps(sample_ticket())
        for output in (
            valid[:-1] + ', "category": "food"}',
            valid[:-1] + ', "extra": {"route": "nurse", "route": "food"}}',
            valid.replace("0.97", "NaN"), valid.replace("0.97", "Infinity"),
            valid.replace("0.97", "-Infinity"), valid.replace("0.97", "1e999"),
        ):
            with self.subTest(output=output[-50:]):
                with self.assertRaises(TicketValidationError):
                    parse_ticket_json(output)

    def test_invalid_utf8_and_wrong_input_types_rejected(self):
        for output in (b"\xff", json.dumps(sample_ticket()).encode("utf-16"),
                       b"\xef\xbb\xbf" + json.dumps(sample_ticket()).encode(), None, {}, 123):
            with self.subTest(output=output):
                with self.assertRaises(TicketValidationError):
                    parse_ticket_json(output)
        self.assertEqual(parse_ticket_json(json.dumps(sample_ticket()).encode()), sample_ticket())

    def test_resource_limit_parse_errors_are_validation_errors(self):
        valid = json.dumps(sample_ticket())
        with self.assertRaises(TicketValidationError):
            parse_ticket_json(valid.replace("0.97", "9" * 5000))
        with self.assertRaises(TicketValidationError):
            parse_ticket_json("[" * 2000 + "0" + "]" * 2000)

    def test_caller_owned_metadata_cannot_be_overwritten(self):
        ticket = sample_ticket()
        metadata = {field: ticket[field] for field in
                    ("ticket_id", "room", "raw_text", "language", "status", "created_at")}
        self.assertEqual(parse_ticket_json(json.dumps(ticket), metadata), ticket)
        for field in metadata:
            changed = sample_ticket(**{field: {
                "ticket_id": "attacker", "room": "another room", "raw_text": "clean my room",
                "language": "fr", "status": "done", "created_at": "2026-10-09T15:00:00Z",
            }[field]})
            with self.subTest(field=field):
                with self.assertRaises(TicketValidationError):
                    validate_ticket(changed, metadata)
        with self.assertRaises(TicketValidationError):
            enforce_immutable_metadata(ticket, {"confidence": 0.97})

    def test_schema_has_exact_plan_fields_and_no_additional_properties(self):
        schema_path = Path(__file__).parents[1] / "ticket.schema.json"
        schema = json.loads(schema_path.read_text())
        self.assertEqual(set(schema["required"]), set(sample_ticket()))
        self.assertEqual(set(schema["properties"]), set(sample_ticket()))
        self.assertIs(schema["additionalProperties"], False)


if __name__ == "__main__":
    unittest.main()
