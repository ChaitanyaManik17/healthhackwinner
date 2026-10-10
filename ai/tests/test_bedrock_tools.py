"""Offline regression tests: fakes only; never load or use AWS credentials."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import csv
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from ai import bedrock_probe, review_phrases
from ai.bedrock_client import (
    BedrockConfigurationError, BedrockResponseError, DEFAULT_MODEL_ID,
    invoke_converse, local_configuration_check, make_bedrock_client,
    resolve_model_id, resolve_profile, resolve_region, safe_error_code,
)
from ai.validate_ticket import ROUTES


TIMESTAMP = "2026-10-09T14:03:00Z"
REGION = "us-east-1"  # Explicit test fixture only; production has no region default.


def phrase(row_id="01", text="Can I get an extra pillow?", category="housekeeping", language="en"):
    return {
        "id": row_id, "text": text, "language": language,
        "expected_category": category, "expected_priority": ROUTES[category][1],
        "note": "Synthetic proposed test label",
    }


def model_ticket(metadata, category="housekeeping", confidence=0.95):
    department, priority, escalate = ROUTES[category]
    return {
        **metadata, "category": category, "department": department,
        "priority": priority, "confidence": confidence,
        "escalate_to_nurse": escalate, "reason": "Synthetic test response",
    }


def envelope(text, stop_reason="end_turn"):
    return {
        "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
        "stopReason": stop_reason,
        "usage": {"inputTokens": 9, "outputTokens": 12, "totalTokens": 21},
        "metrics": {"latencyMs": 17},
    }


class FakeClient:
    def __init__(self, response=None, category="housekeeping", confidence=0.95, mutate=None):
        self.response = response
        self.category = category
        self.confidence = confidence
        self.mutate = mutate
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        if self.response is not None:
            return self.response
        metadata = json.loads(kwargs["messages"][0]["content"][0]["text"])
        ticket = model_ticket(metadata, self.category, self.confidence)
        if self.mutate:
            ticket.update(self.mutate)
        return envelope(json.dumps(ticket))


class FakeAwsError(Exception):
    def __init__(self, code="AccessDeniedException"):
        self.response = {"Error": {"Code": code, "Message": "NEVER_PRINT_THIS_SECRET"}}
        super().__init__("NEVER_PRINT_THIS_SECRET")


class ConfigurationTests(unittest.TestCase):
    def test_region_is_explicit_or_environment_only(self):
        self.assertEqual(resolve_region(REGION, {}), REGION)
        self.assertEqual(resolve_region(None, {"AWS_REGION": "eu-west-1"}), "eu-west-1")
        self.assertEqual(resolve_region(None, {"AWS_DEFAULT_REGION": "ap-south-1"}), "ap-south-1")
        self.assertEqual(resolve_region(REGION, {"AWS_REGION": "eu-west-1"}), REGION)
        with self.assertRaises(BedrockConfigurationError) as caught:
            resolve_region(None, {})
        self.assertEqual(caught.exception.code, "MissingRegion")

    def test_invalid_region_model_profile_rejected(self):
        for fn, value in ((resolve_region, "bad\nregion"), (resolve_model_id, "bad\nmodel"), (resolve_profile, "bad\nprofile")):
            with self.subTest(fn=fn.__name__), self.assertRaises(BedrockConfigurationError):
                fn(value, {})
        self.assertEqual(resolve_model_id(None, {}), DEFAULT_MODEL_ID)
        self.assertEqual(resolve_model_id(None, {"BEDROCK_MODEL_ID": "test.model-v1:0"}), "test.model-v1:0")

    def test_static_presence_check_returns_no_secret_values(self):
        with tempfile.TemporaryDirectory() as directory:
            credentials = Path(directory) / "credentials"
            config = Path(directory) / "config"
            credentials.write_text("[workshop]\naws_access_key_id=SECRET_KEY\naws_secret_access_key=SECRET_VALUE\n")
            config.write_text("[profile workshop]\nregion=eu-west-1\n")
            result = local_configuration_check(REGION, "workshop", {
                "AWS_CONFIG_FILE": str(config), "AWS_SHARED_CREDENTIALS_FILE": str(credentials),
            })
        self.assertTrue(result["locally_ready"])
        self.assertTrue(result["profile_credentials_present"])
        self.assertFalse(result["credentials_validated"])
        self.assertEqual(result["network_calls"], 0)
        self.assertNotIn("SECRET", json.dumps(result))

    def test_profile_region_does_not_silently_choose_paid_region(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            config.write_text("[default]\nregion=us-east-1\n")
            result = local_configuration_check(env={
                "AWS_CONFIG_FILE": str(config), "AWS_SHARED_CREDENTIALS_FILE": str(Path(directory) / "absent"),
                "AWS_ACCESS_KEY_ID": "SYNTHETIC", "AWS_SECRET_ACCESS_KEY": "SYNTHETIC",
            })
        self.assertTrue(result["profile_region_configured"])
        self.assertEqual(result["region_error"], "MissingRegion")
        self.assertFalse(result["locally_ready"])

    def test_container_presence_is_checked_without_contacting_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            result = local_configuration_check(REGION, env={
                "AWS_CONFIG_FILE": str(Path(directory) / "absent-config"),
                "AWS_SHARED_CREDENTIALS_FILE": str(Path(directory) / "absent-credentials"),
                "AWS_CONTAINER_CREDENTIALS_FULL_URI": "http://example.invalid/SECRET",
                "AWS_CONTAINER_AUTHORIZATION_TOKEN": "SECRET_TOKEN",
            })
        self.assertTrue(result["container_credentials_configured"])
        self.assertTrue(result["locally_ready"])
        self.assertEqual(result["network_calls"], 0)
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertNotIn("http", json.dumps(result))

    def test_safe_errors_never_include_full_aws_message(self):
        self.assertEqual(safe_error_code(FakeAwsError()), "AccessDeniedException")
        self.assertEqual(safe_error_code(FakeAwsError("SECRET.with\nunsafe.characters")), "AWSServiceError")
        self.assertEqual(safe_error_code(RuntimeError("SECRET")), "UnexpectedError")

    def test_missing_selected_profile_not_masked_by_container_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            result = local_configuration_check(REGION, "missing", {
                "AWS_CONFIG_FILE": str(Path(directory) / "absent-config"),
                "AWS_SHARED_CREDENTIALS_FILE": str(Path(directory) / "absent-credentials"),
                "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI": "/synthetic/container/path",
            })
        self.assertTrue(result["container_credentials_configured"])
        self.assertFalse(result["locally_ready"])
        self.assertEqual(result["profile_error"], "ProfileNotFound")

    def test_environment_web_identity_not_used_with_selected_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            config.write_text("[profile workshop]\nregion=us-east-1\n")
            result = local_configuration_check(REGION, "workshop", {
                "AWS_CONFIG_FILE": str(config),
                "AWS_SHARED_CREDENTIALS_FILE": str(Path(directory) / "absent-credentials"),
                "AWS_ROLE_ARN": "SYNTHETIC_ROLE", "AWS_WEB_IDENTITY_TOKEN_FILE": "SYNTHETIC_TOKEN_FILE",
            })
        self.assertFalse(result["web_identity_configured"])
        self.assertFalse(result["locally_ready"])

    def test_client_timeouts_attempts_and_metadata_default(self):
        captured = {}

        class FakeSession:
            def __init__(self, **kwargs):
                captured["session"] = kwargs

            def client(self, service, **kwargs):
                captured["service"] = service
                captured.update(kwargs)
                return "FAKE_CLIENT"

        class FakeConfig:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        with patch.dict("sys.modules", {
            "boto3": types.SimpleNamespace(Session=FakeSession),
            "botocore.config": types.SimpleNamespace(Config=FakeConfig),
        }), patch.dict("os.environ", {}, clear=True):
            self.assertEqual(make_bedrock_client(REGION, "workshop"), "FAKE_CLIENT")
            import os
            self.assertEqual(os.environ["AWS_EC2_METADATA_DISABLED"], "true")
        self.assertEqual(captured["service"], "bedrock-runtime")
        self.assertEqual(captured["config"].kwargs, {
            "connect_timeout": 3, "read_timeout": 8,
            "retries": {"total_max_attempts": 1, "mode": "standard"},
        })


class ConverseTests(unittest.TestCase):
    def test_text_request_and_usage(self):
        client = FakeClient(response=envelope("Hello"))
        result = invoke_converse(client, DEFAULT_MODEL_ID, "Synthetic hello", "Synthetic prompt", 32)
        self.assertEqual(result.text, "Hello")
        self.assertEqual(result.usage["totalTokens"], 21)
        self.assertEqual(result.server_latency_ms, 17)
        self.assertGreaterEqual(result.latency_ms, 0)
        self.assertEqual(client.calls[0]["inferenceConfig"], {"maxTokens": 32, "temperature": 0})
        self.assertEqual(client.calls[0]["system"], [{"text": "Synthetic prompt"}])

    def test_incomplete_stop_reasons_reject_even_complete_looking_json(self):
        for reason in ("max_tokens", "guardrail_intervened", "tool_use", "content_filtered", None):
            with self.subTest(reason=reason), self.assertRaises(BedrockResponseError) as caught:
                invoke_converse(FakeClient(response=envelope("{}", reason)), DEFAULT_MODEL_ID, "Synthetic")
            self.assertEqual(caught.exception.code, "IncompleteModelResponse")
            self.assertEqual(caught.exception.raw_text, "{}")

    def test_mixed_output_blocks_rejected(self):
        response = envelope("{}")
        response["output"]["message"]["content"].append({"toolUse": {}})
        with self.assertRaises(BedrockResponseError):
            invoke_converse(FakeClient(response=response), DEFAULT_MODEL_ID, "Synthetic")

    def test_nonfinite_latency_not_serialized(self):
        for latency in (float("nan"), float("inf"), -1, True, "17"):
            with self.subTest(latency=latency):
                response = envelope("Hello")
                response["metrics"]["latencyMs"] = latency
                result = invoke_converse(FakeClient(response=response), DEFAULT_MODEL_ID, "Synthetic")
                self.assertIsNone(result.server_latency_ms)


class ProbeTests(unittest.TestCase):
    def test_live_acknowledgement_required(self):
        factory = unittest.mock.Mock()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            bedrock_probe.main(["--region", REGION], client_factory=factory)
        self.assertEqual(caught.exception.code, 2)
        factory.assert_not_called()

    def test_check_only_never_creates_client_and_missing_config_is_nonzero(self):
        factory = unittest.mock.Mock()
        with tempfile.TemporaryDirectory() as directory:
            env = {
                "AWS_CONFIG_FILE": str(Path(directory) / "absent-config"),
                "AWS_SHARED_CREDENTIALS_FILE": str(Path(directory) / "absent-credentials"),
            }
            output = io.StringIO()
            with patch.dict("os.environ", env, clear=True), redirect_stdout(output):
                code = bedrock_probe.main(["--check-only"], client_factory=factory)
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(output.getvalue())["live_call_executed"])
        factory.assert_not_called()

    def test_check_only_with_environment_credentials_returns_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            env = {
                "AWS_CONFIG_FILE": str(Path(directory) / "absent-config"),
                "AWS_SHARED_CREDENTIALS_FILE": str(Path(directory) / "absent-credentials"),
                "AWS_REGION": REGION, "AWS_ACCESS_KEY_ID": "SECRET_ID",
                "AWS_SECRET_ACCESS_KEY": "SECRET_KEY",
            }
            with patch.dict("os.environ", env, clear=True), redirect_stdout(output):
                self.assertEqual(bedrock_probe.main(["--check-only"]), 0)
        self.assertNotIn("SECRET", output.getvalue())
        self.assertFalse(json.loads(output.getvalue())["credentials_validated"])

    def test_fixed_synthetic_probe_writes_evidence(self):
        client = FakeClient(response=envelope("Hello"))
        factory = unittest.mock.Mock(return_value=client)
        with tempfile.TemporaryDirectory() as directory:
            evidence_path = Path(directory) / "evidence.json"
            with redirect_stdout(io.StringIO()):
                code = bedrock_probe.main([
                    "--region", REGION, "--profile", "workshop", "--synthetic-only",
                    "--output", str(evidence_path),
                ], client_factory=factory)
            evidence = json.loads(evidence_path.read_text())
        self.assertEqual(code, 0)
        self.assertEqual(evidence["status"], "ok")
        self.assertEqual(evidence["model_id"], DEFAULT_MODEL_ID)
        factory.assert_called_once_with(REGION, "workshop")
        self.assertEqual(client.calls[0]["messages"][0]["content"][0]["text"], bedrock_probe.SYNTHETIC_HELLO)

    def test_probe_aws_error_outputs_safe_code_only(self):
        output = io.StringIO()
        client = FakeClient(response=FakeAwsError())
        with redirect_stdout(output):
            code = bedrock_probe.main(["--region", REGION, "--synthetic-only"], client_factory=lambda *_: client)
        self.assertEqual(code, 1)
        self.assertNotIn("NEVER_PRINT", output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["error_code"], "AccessDeniedException")


class PhraseInputTests(unittest.TestCase):
    def test_unique_ids_labels_and_limits_rejected_before_model_call(self):
        client = FakeClient()
        invalid = [
            [phrase(), phrase()],
            [phrase(), {**phrase("02"), "id": "../bad"}],
            [phrase(), {**phrase("02"), "text": "x" * 2001}],
            [phrase(), {**phrase("02"), "expected_priority": "high"}],
            [phrase(), {**phrase("02"), "language": "en\n"}],
            [],
        ]
        for rows in invalid:
            with self.subTest(rows=len(rows)), self.assertRaises(review_phrases.PhraseInputError):
                review_phrases.review_rows(rows, client, DEFAULT_MODEL_ID, "Synthetic prompt", REGION)
        self.assertEqual(client.calls, [])

    def test_csv_has_exact_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "phrases.csv"
            csv_path.write_text("id,text\n01,Synthetic hello\n")
            with self.assertRaises(review_phrases.PhraseInputError):
                review_phrases.load_phrase_csv(csv_path)

    def test_csv_preserves_text_verbatim(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "phrases.csv"
            row = phrase(text="  Synthetic, pillow request\nsecond line  ")
            with csv_path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=review_phrases.REQUIRED_COLUMNS)
                writer.writeheader()
                writer.writerow(row)
            self.assertEqual(review_phrases.load_phrase_csv(csv_path)[0]["text"], row["text"])


class PhraseReviewTests(unittest.TestCase):
    def run_review(self, client, row=None):
        return review_phrases.review_rows(
            [row or phrase()], client, DEFAULT_MODEL_ID, "Synthetic prompt", REGION,
            created_at=TIMESTAMP,
        )

    def test_valid_result_matches_expected_and_preserves_metadata(self):
        client = FakeClient()
        report = self.run_review(client)
        result = report["results"][0]
        self.assertFalse(result["fallback_used"])
        self.assertTrue(result["model_matches_expected"])
        self.assertEqual(result["final_ticket"]["room"], "SYNTHETIC-01")
        self.assertEqual(result["final_ticket"]["ticket_id"], "t_phase0_01")
        self.assertEqual(client.calls[0]["inferenceConfig"], {"maxTokens": 512, "temperature": 0})
        payload = json.loads(client.calls[0]["messages"][0]["content"][0]["text"])
        self.assertEqual(payload["created_at"], TIMESTAMP)
        self.assertEqual(set(payload), {"ticket_id", "room", "raw_text", "language", "status", "created_at"})
        self.assertTrue(report["summary"]["human_review_pending"])
        self.assertFalse(report["summary"]["safety_readiness_established"])

    def test_invalid_json_nurse_fallback_retains_raw_evidence(self):
        report = self.run_review(FakeClient(response=envelope("not JSON")))
        result = report["results"][0]
        self.assertEqual(result["raw_model_output"], "not JSON")
        self.assertEqual(result["fallback_cause"], "invalid_ticket_output")
        self.assertEqual(result["final_ticket"]["category"], "unclear")
        self.assertEqual(result["final_ticket"]["department"], "nurse")
        self.assertEqual(result["final_ticket"]["confidence"], 0)
        self.assertEqual(report["summary"]["model_errors"], 1)

    def test_model_metadata_mutation_is_rejected(self):
        report = self.run_review(FakeClient(mutate={"room": "OTHER-ROOM", "raw_text": "REWRITTEN"}))
        result = report["results"][0]
        self.assertEqual(result["fallback_cause"], "invalid_ticket_output")
        self.assertEqual(result["final_ticket"]["room"], "SYNTHETIC-01")
        self.assertEqual(result["final_ticket"]["raw_text"], phrase()["text"])
        self.assertTrue(any("metadata" in error for error in result["validation_failures"]))

    def test_low_confidence_boundary(self):
        low = self.run_review(FakeClient(confidence=0.7999))["results"][0]
        self.assertEqual(low["fallback_cause"], "low_confidence")
        self.assertEqual(low["model_result"]["category"], "housekeeping")
        self.assertEqual(low["final_ticket"]["department"], "nurse")
        accepted = self.run_review(FakeClient(confidence=0.80))["results"][0]
        self.assertFalse(accepted["fallback_used"])

    def test_unsupported_language_and_empty_text_never_invoke_model(self):
        client = FakeClient()
        rows = [phrase(language="es", category="unclear"), phrase("02", text="  ", category="unclear")]
        report = review_phrases.review_rows(rows, client, DEFAULT_MODEL_ID, "Synthetic prompt", REGION, created_at=TIMESTAMP)
        self.assertEqual(client.calls, [])
        self.assertEqual(report["summary"]["model_accuracy"], 0)
        self.assertEqual(report["summary"]["final_route_accuracy"], 1)
        self.assertEqual(report["summary"]["model_valid_tickets"], 0)
        self.assertFalse(report["summary"]["safety_readiness_established"])

    def test_incomplete_response_forces_nurse_fallback(self):
        metadata = review_phrases.phrase_metadata(phrase(), TIMESTAMP)
        client = FakeClient(response=envelope(json.dumps(model_ticket(metadata)), "max_tokens"))
        result = self.run_review(client)["results"][0]
        self.assertEqual(result["fallback_cause"], "model_response_error")
        self.assertEqual(result["error_code"], "IncompleteModelResponse")
        self.assertIsNotNone(result["raw_model_output"])
        self.assertEqual(result["final_ticket"]["department"], "nurse")

    def test_per_row_aws_exception_never_leaks_credentials(self):
        report = self.run_review(FakeClient(response=FakeAwsError()), phrase(category="unclear"))
        self.assertNotIn("NEVER_PRINT", json.dumps(report))
        self.assertEqual(report["summary"]["model_accuracy"], 0)
        self.assertEqual(report["summary"]["final_route_accuracy"], 1)
        self.assertEqual(report["summary"]["model_errors"], 1)
        self.assertFalse(report["summary"]["safety_readiness_established"])

    def test_model_missed_urgent_case_counted_before_local_fallback(self):
        row = phrase(text="Synthetic chest tightness", category="urgent_clinical")
        report = self.run_review(FakeClient(category="food", confidence=0.2), row)
        self.assertEqual(report["summary"]["model_urgent_miss_count"], 1)
        self.assertEqual(report["summary"]["final_route_urgent_miss_count"], 0)
        self.assertEqual(report["results"][0]["final_ticket"]["department"], "nurse")

    def test_high_confidence_wrong_route_remains_visible_for_human_review(self):
        row = phrase(text="Synthetic chest tightness", category="urgent_clinical")
        report = self.run_review(FakeClient(category="food"), row)
        self.assertEqual(report["summary"]["model_urgent_miss_count"], 1)
        self.assertEqual(report["summary"]["final_route_urgent_miss_count"], 1)
        self.assertFalse(report["summary"]["safety_readiness_established"])

    def test_main_invalid_input_rejects_before_client_creation(self):
        factory = unittest.mock.Mock()
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "bad.csv"
            csv_path.write_text("id,text\n01,Synthetic\n")
            with redirect_stdout(io.StringIO()):
                code = review_phrases.main([
                    "--input", str(csv_path), "--region", REGION, "--synthetic-only",
                ], client_factory=factory)
        self.assertEqual(code, 2)
        factory.assert_not_called()

    def test_main_saves_report_and_prints_summary_only(self):
        client = FakeClient()
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            csv_path = directory / "phrases.csv"
            prompt_path = directory / "prompt.txt"
            output_path = directory / "report.json"
            prompt_path.write_text("Synthetic prompt")
            with csv_path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=review_phrases.REQUIRED_COLUMNS)
                writer.writeheader()
                writer.writerow(phrase())
            stdout = io.StringIO()
            with patch.object(review_phrases, "DEFAULT_PROMPT", prompt_path), redirect_stdout(stdout):
                code = review_phrases.main([
                    "--input", str(csv_path), "--region", REGION, "--synthetic-only",
                    "--output", str(output_path),
                ], client_factory=lambda *_: client)
            report = json.loads(output_path.read_text())
        self.assertEqual(code, 0)
        self.assertNotIn("raw_model_output", stdout.getvalue())
        self.assertIn("raw_model_output", report["results"][0])
        self.assertEqual(report["results"][0]["human_review"], "pending")


if __name__ == "__main__":
    unittest.main()
