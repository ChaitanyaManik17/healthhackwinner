"""Manually inspect synthetic Phase 0 phrases against the proposed prompt.

This is a review CLI, not the Phase 1 /classify API or Ketan's scoring script.
Every report needs human review; its numbers do not establish clinical safety.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping
import csv
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any

from ai.bedrock_client import (
    BedrockResponseError, CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS,
    MAX_ATTEMPTS, invoke_converse, make_bedrock_client, resolve_model_id,
    resolve_profile, resolve_region, safe_error_code, utc_timestamp,
    write_json_report,
)
from ai.validate_ticket import ROUTES, TicketValidationError, parse_ticket_json, validate_ticket


AI_DIRECTORY = Path(__file__).resolve().parent
DEFAULT_INPUT = AI_DIRECTORY / "fixtures" / "provisional_phrases.csv"
DEFAULT_PROMPT = AI_DIRECTORY / "system_prompt.txt"
REQUIRED_COLUMNS = ("id", "text", "language", "expected_category", "expected_priority", "note")
MAX_TEXT_CHARACTERS = 2000
MAX_ROWS = 1000
MIN_CONFIDENCE = 0.80
_SAFE_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
_LANGUAGE = re.compile(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")
FALLBACK_REASON = "Phase 0 review requires a nurse to review this request."


class PhraseInputError(ValueError):
    """Input rejected before creating a Bedrock client or making any call."""


def validate_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Validate the complete input first, including uniqueness and labels."""
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        if row_number > MAX_ROWS + 1:
            raise PhraseInputError(f"CSV exceeds the {MAX_ROWS}-row limit")
        if set(row) != set(REQUIRED_COLUMNS) or any(not isinstance(row.get(key), str) for key in REQUIRED_COLUMNS):
            raise PhraseInputError(f"row {row_number}: expected exactly the six documented string columns")
        clean = dict(row)
        row_id = clean["id"]
        if not _SAFE_ID.fullmatch(row_id) or row_id in seen:
            raise PhraseInputError(f"row {row_number}: id must be unique and use 1 to 64 letters, digits, underscores or hyphens")
        seen.add(row_id)
        if len(clean["text"]) > MAX_TEXT_CHARACTERS or "\x00" in clean["text"]:
            raise PhraseInputError(f"row {row_number}: text exceeds the length limit or contains a null character")
        if not _LANGUAGE.fullmatch(clean["language"]):
            raise PhraseInputError(f"row {row_number}: language must be a language tag such as en or es")
        category = clean["expected_category"]
        if category not in ROUTES or clean["expected_priority"] != ROUTES[category][1]:
            raise PhraseInputError(f"row {row_number}: expected category and priority must match the ticket routing contract")
        if len(clean["note"]) > 1000:
            raise PhraseInputError(f"row {row_number}: note exceeds the 1000-character limit")
        result.append(clean)
    if not result:
        raise PhraseInputError("CSV must contain at least one phrase")
    return result


def load_phrase_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        if reader.fieldnames is None or len(reader.fieldnames) != len(REQUIRED_COLUMNS) or set(reader.fieldnames) != set(REQUIRED_COLUMNS):
            raise PhraseInputError("CSV header must contain exactly: " + ", ".join(REQUIRED_COLUMNS))
        try:
            return validate_rows(reader)
        except csv.Error as exc:
            raise PhraseInputError("CSV could not be parsed") from exc


def phrase_metadata(row: Mapping[str, str], created_at: str) -> dict[str, str]:
    return {
        "ticket_id": f"t_phase0_{row['id']}",
        "room": "SYNTHETIC-01",
        "raw_text": row["text"],
        "language": row["language"],
        "status": "new",
        "created_at": created_at,
    }


def nurse_fallback(metadata: Mapping[str, str]) -> dict[str, Any]:
    ticket: dict[str, Any] = {
        **metadata,
        "category": "unclear",
        "department": "nurse",
        "priority": "high",
        "confidence": 0,
        "escalate_to_nurse": True,
        "reason": FALLBACK_REASON,
    }
    return validate_ticket(ticket, metadata)


def _matches_expected(ticket: Mapping[str, Any] | None, expected: Mapping[str, Any]) -> bool:
    return ticket is not None and all(ticket[key] == expected[key] for key in ("category", "department", "priority"))


def _unsafe_nurse_route(ticket: Mapping[str, Any] | None, expected: Mapping[str, Any]) -> bool:
    return bool(ticket is not None and expected["department"] == "nurse" and (
        ticket["department"] != "nurse" or ticket["priority"] != "high"
        or ticket["escalate_to_nurse"] is not True
    ))


def review_phrase(
    row: Mapping[str, str], client: Any, model_id: str, prompt: str,
    created_at: str,
) -> dict[str, Any]:
    """Retain raw model evidence and distinguish it from the local final route."""
    metadata = phrase_metadata(row, created_at)
    department, priority, escalate = ROUTES[row["expected_category"]]
    expected = {
        "category": row["expected_category"], "department": department,
        "priority": priority, "escalate_to_nurse": escalate,
    }
    result: dict[str, Any] = {
        "id": row["id"], "input": metadata, "note": row["note"], "expected": expected,
        "model_call_attempted": False, "model_response_received": False,
        "raw_model_output": None, "model_result": None, "model_output_valid": False,
        "stop_reason": None, "latency_ms": None, "usage": {},
        "validation_failures": [], "error_code": None, "fallback_used": False,
        "fallback_cause": None, "human_review": "pending",
    }
    final_ticket = nurse_fallback(metadata)
    # The Phase 0 plan limits the MVP to English. This does not translate or
    # infer safety from a clinical keyword heuristic.
    if row["language"] != "en":
        result["fallback_cause"] = "unsupported_language"
    elif not row["text"].strip():
        result["fallback_cause"] = "empty_text"
    else:
        start = time.perf_counter()
        result["model_call_attempted"] = True
        try:
            response = invoke_converse(
                client, model_id, json.dumps(metadata, ensure_ascii=False),
                system_prompt=prompt, max_tokens=512,
            )
            result.update({
                "raw_model_output": response.text, "stop_reason": response.stop_reason,
                "latency_ms": response.latency_ms, "usage": response.usage,
                "model_response_received": True,
            })
            try:
                ticket = parse_ticket_json(response.text, metadata)
            except TicketValidationError as exc:
                result["validation_failures"] = list(exc.errors)
                result["fallback_cause"] = "invalid_ticket_output"
            else:
                result["model_result"] = ticket
                result["model_output_valid"] = True
                if ticket["confidence"] < MIN_CONFIDENCE:
                    result["fallback_cause"] = "low_confidence"
                else:
                    final_ticket = ticket
        except Exception as exc:
            result["error_code"] = safe_error_code(exc)
            result["fallback_cause"] = "model_response_error" if isinstance(exc, BedrockResponseError) else "model_call_error"
            result["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            if isinstance(exc, BedrockResponseError):
                result.update({
                    "raw_model_output": exc.raw_text, "stop_reason": exc.stop_reason,
                    "model_response_received": True,
                    "validation_failures": [exc.code],
                })
    result.update({
        "fallback_used": result["fallback_cause"] is not None,
        "final_ticket": final_ticket,
        "model_matches_expected": _matches_expected(result["model_result"], expected),
        "final_route_matches_expected": _matches_expected(final_ticket, expected),
        "model_missed_nurse_case": _unsafe_nurse_route(result["model_result"], expected),
        "final_route_missed_nurse_case": _unsafe_nurse_route(final_ticket, expected),
    })
    return result


def review_rows(
    rows: Iterable[Mapping[str, Any]], client: Any, model_id: str, prompt: str,
    region: str, *, created_at: str | None = None,
) -> dict[str, Any]:
    rows = validate_rows(rows)  # No partial cloud execution on bad input.
    if not isinstance(prompt, str) or not prompt.strip():
        raise PhraseInputError("system prompt must be nonempty")
    recorded_at = created_at or utc_timestamp()
    results = [review_phrase(row, client, model_id, prompt, recorded_at) for row in rows]
    model_errors = sum(row["fallback_cause"] in {
        "model_call_error", "model_response_error", "invalid_ticket_output",
    } for row in results)
    model_matches = sum(row["model_matches_expected"] for row in results)
    final_matches = sum(row["final_route_matches_expected"] for row in results)
    total = len(results)
    summary = {
        "total_phrases": total,
        "model_calls_attempted": sum(row["model_call_attempted"] for row in results),
        "model_responses_received": sum(row["model_response_received"] for row in results),
        "model_valid_tickets": sum(row["model_output_valid"] for row in results),
        "model_errors": model_errors,
        "fallback_count": sum(row["fallback_used"] for row in results),
        "model_matches_expected": model_matches,
        "model_accuracy": round(model_matches / total, 4),
        "final_route_matches_expected": final_matches,
        "final_route_accuracy": round(final_matches / total, 4),
        "expected_nurse_cases": sum(row["expected"]["department"] == "nurse" for row in results),
        "model_urgent_miss_count": sum(row["model_missed_nurse_case"] for row in results),
        "final_route_urgent_miss_count": sum(row["final_route_missed_nurse_case"] for row in results),
        "human_review_pending": True,
        "safety_readiness_established": False,
        "run_status": "completed_with_model_errors" if model_errors else "completed_pending_human_review",
    }
    return {
        "report_version": 1, "recorded_at": recorded_at,
        "synthetic_only": True, "purpose": "Phase 0 manual phrase review",
        "region": region, "model_id": model_id,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "confidence_threshold": MIN_CONFIDENCE,
        "io_timeout_seconds": {"connect": CONNECT_TIMEOUT_SECONDS, "read": READ_TIMEOUT_SECONDS},
        "max_attempts": MAX_ATTEMPTS,
        "timeout_scope": "SDK connect/read I/O; not a hard wall-clock deadline",
        "accuracy_denominator": "All input phrases, including local fallbacks and model failures",
        "urgent_miss_definition": "Expected nurse/high cases routed elsewhere; includes urgent_clinical and unclear",
        "labels_status": "proposed; pending David and Ketan review",
        "summary": summary, "results": results,
    }


def main(argv: list[str] | None = None, *, client_factory: Any = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Synthetic phrase CSV with the six documented columns")
    parser.add_argument("--region", help="Team's AWS region (or AWS_REGION / AWS_DEFAULT_REGION)")
    parser.add_argument("--profile", help="Local AWS profile; never pass credential values here")
    parser.add_argument("--model-id", help="Bedrock model ID (or BEDROCK_MODEL_ID; default amazon.nova-micro-v1:0)")
    parser.add_argument("--synthetic-only", action="store_true", help="Confirm every input phrase is synthetic; required before any model calls")
    parser.add_argument("--output", type=Path, help="JSON report (default ai/reviews/phase0_<UTC timestamp>.json)")
    args = parser.parse_args(argv)
    if not args.synthetic_only:
        parser.error("--synthetic-only is required: confirm the CSV contains no real patient information")
    try:
        # Complete validation and prompt loading before client creation.
        rows = load_phrase_csv(args.input)
        prompt = DEFAULT_PROMPT.read_text(encoding="utf-8")
        if not prompt.strip():
            raise PhraseInputError("system prompt must be nonempty")
        region = resolve_region(args.region)
        profile = resolve_profile(args.profile)
        model_id = resolve_model_id(args.model_id)
        recorded_at = utc_timestamp()
        output = args.output or AI_DIRECTORY / "reviews" / ("phase0_" + recorded_at.replace("-", "").replace(":", "") + ".json")
        factory = client_factory or make_bedrock_client
        client = factory(region, profile)
        report = review_rows(rows, client, model_id, prompt, region, created_at=recorded_at)
        write_json_report(output, report)
    except (PhraseInputError, UnicodeError) as exc:
        print(json.dumps({"status": "input_rejected", "error": str(exc) if isinstance(exc, PhraseInputError) else "InputEncodingError"}))
        return 2
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_code": safe_error_code(exc)}))
        return 1
    print(json.dumps({"report": str(output.resolve()), **report["summary"]}, ensure_ascii=False))
    return 1 if report["summary"]["model_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
