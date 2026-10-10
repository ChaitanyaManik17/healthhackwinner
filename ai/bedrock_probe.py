"""Run a single fixed synthetic hello, or inspect local AWS setup offline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ai.bedrock_client import (
    CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS, MAX_ATTEMPTS,
    invoke_converse, local_configuration_check, make_bedrock_client,
    resolve_model_id, resolve_profile, resolve_region, safe_error_code,
    utc_timestamp, write_json_report,
)


SYNTHETIC_HELLO = "Synthetic setup test: reply with exactly Hello."


def main(argv: list[str] | None = None, *, client_factory: Any = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", help="Team's AWS region (or AWS_REGION / AWS_DEFAULT_REGION); required for live calls")
    parser.add_argument("--profile", help="Local AWS profile; never pass credential values here")
    parser.add_argument("--model-id", help="Bedrock model ID (or BEDROCK_MODEL_ID; default amazon.nova-micro-v1:0)")
    parser.add_argument("--check-only", action="store_true", help="Inspect local configuration presence without resolving credentials or making network calls")
    parser.add_argument("--synthetic-only", action="store_true", help="Acknowledge synthetic input only; required before the live hello call")
    parser.add_argument("--output", type=Path, help="Also save the JSON evidence to this path")
    args = parser.parse_args(argv)
    if not args.check_only and not args.synthetic_only:
        parser.error("live calls require --synthetic-only; this sends one fixed synthetic hello")

    evidence: dict[str, Any] = {"recorded_at": utc_timestamp(), "live_call_executed": False}
    exit_code = 0
    try:
        evidence["model_id"] = resolve_model_id(args.model_id)
        if args.check_only:
            evidence.update(local_configuration_check(args.region, args.profile))
            evidence["status"] = "local_configuration_checked"
            exit_code = 0 if evidence["locally_ready"] else 1
        else:
            region = resolve_region(args.region)
            profile = resolve_profile(args.profile)
            evidence.update({
                "region": region, "profile": profile or "default", "synthetic_only": True,
                "io_timeout_seconds": {"connect": CONNECT_TIMEOUT_SECONDS, "read": READ_TIMEOUT_SECONDS},
                "max_attempts": MAX_ATTEMPTS,
                "timeout_scope": "SDK connect/read I/O; not a hard wall-clock deadline",
            })
            factory = client_factory or make_bedrock_client
            client = factory(region, profile)
            evidence["live_call_executed"] = True
            result = invoke_converse(client, evidence["model_id"], SYNTHETIC_HELLO, max_tokens=32)
            evidence.update({
                "status": "ok", "response": result.text, "stop_reason": result.stop_reason,
                "latency_ms": result.latency_ms, "server_latency_ms": result.server_latency_ms,
                "usage": result.usage,
            })
    except Exception as exc:
        evidence.update({"status": "failed", "error_code": safe_error_code(exc)})
        exit_code = 1
    if args.output:
        try:
            write_json_report(args.output, evidence)
        except (OSError, ValueError):
            evidence.update({"status": "failed", "report_error_code": "ReportWriteFailed"})
            exit_code = 1
    print(json.dumps(evidence, ensure_ascii=False, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
