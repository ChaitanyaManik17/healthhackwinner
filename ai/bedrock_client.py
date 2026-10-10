"""Small Converse helpers shared by the Phase 0 command-line tools.

This is not the Phase 1 classify function. SDK timeouts bound connect/read I/O;
they are not an absolute wall-clock deadline for credential discovery or DNS.
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import time
from typing import Any, Mapping


DEFAULT_MODEL_ID = "amazon.nova-micro-v1:0"
CONNECT_TIMEOUT_SECONDS = 3
READ_TIMEOUT_SECONDS = 8
MAX_ATTEMPTS = 1
_REGION = re.compile(r"[a-z]{2,4}(?:-[a-z]+)+-[0-9]+")
_MODEL = re.compile(r"[A-Za-z0-9_./:-]{1,2048}")
_PROFILE = re.compile(r"[A-Za-z0-9_.@-]{1,128}")
_SAFE_CODE = re.compile(r"[A-Za-z][A-Za-z0-9]{0,79}")
_STOP_REASONS = frozenset({
    "end_turn", "tool_use", "max_tokens", "stop_sequence",
    "guardrail_intervened", "content_filtered", "malformed_model_output",
    "malformed_tool_use", "model_context_window_exceeded",
})
_LOCAL_ERROR_CODES = frozenset({
    "NoCredentialsError", "PartialCredentialsError", "ProfileNotFound",
    "CredentialRetrievalError", "TokenRetrievalError", "SSOTokenLoadError",
    "UnauthorizedSSOTokenError", "NoRegionError", "ConnectTimeoutError",
    "ReadTimeoutError", "EndpointConnectionError", "ProxyConnectionError",
    "SSLError", "ParamValidationError", "InvalidConfigError",
})


class BedrockConfigurationError(ValueError):
    """Safe configuration error; code contains no credential material."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class BedrockResponseError(ValueError):
    """Unexpected/truncated output, with synthetic raw text for review only."""

    def __init__(self, code: str, raw_text: str = "", stop_reason: str | None = None):
        self.code = code
        self.raw_text = raw_text
        self.stop_reason = stop_reason
        super().__init__(code)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def resolve_region(region: str | None = None, env: Mapping[str, str] | None = None) -> str:
    """Require the team's explicitly selected region; never choose one for it."""
    env = os.environ if env is None else env
    candidate = region or env.get("AWS_REGION") or env.get("AWS_DEFAULT_REGION")
    if not candidate or not candidate.strip():
        raise BedrockConfigurationError("MissingRegion")
    candidate = candidate.strip()
    if not _REGION.fullmatch(candidate):
        raise BedrockConfigurationError("InvalidRegion")
    return candidate


def resolve_model_id(model_id: str | None = None, env: Mapping[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    candidate = model_id or env.get("BEDROCK_MODEL_ID") or DEFAULT_MODEL_ID
    if not _MODEL.fullmatch(candidate):
        raise BedrockConfigurationError("InvalidModelId")
    return candidate


def resolve_profile(profile: str | None = None, env: Mapping[str, str] | None = None) -> str | None:
    env = os.environ if env is None else env
    candidate = profile or env.get("AWS_PROFILE") or env.get("AWS_DEFAULT_PROFILE")
    if candidate is not None and not _PROFILE.fullmatch(candidate):
        raise BedrockConfigurationError("InvalidProfile")
    return candidate


def safe_error_code(exc: Exception) -> str:
    """Do not log repr/str of SDK errors: they may contain request or secrets."""
    if isinstance(exc, (BedrockConfigurationError, BedrockResponseError)):
        return exc.code
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        error = response.get("Error", {})
        code = error.get("Code") if isinstance(error, dict) else None
        if isinstance(code, str) and _SAFE_CODE.fullmatch(code):
            return code
        return "AWSServiceError"
    name = type(exc).__name__
    if name in _LOCAL_ERROR_CODES:
        return name
    if isinstance(exc, ModuleNotFoundError):
        return "DependencyMissing"
    if isinstance(exc, OSError):
        return "LocalFileError"
    return "UnexpectedError"


def _read_config(path: Path) -> tuple[configparser.RawConfigParser, bool]:
    config = configparser.RawConfigParser(interpolation=None)
    try:
        if path.is_file():
            with path.open(encoding="utf-8") as handle:
                config.read_file(handle)
    except (OSError, configparser.Error, UnicodeError):
        return configparser.RawConfigParser(interpolation=None), True
    return config, False


def local_configuration_check(
    region: str | None = None, profile: str | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Inspect configuration presence only, without SDK credential resolution.

    This never runs credential_process, refreshes SSO, calls STS, or contacts
    instance/container metadata. Presence does not prove credentials are valid.
    """
    env = os.environ if env is None else env
    selected_profile = resolve_profile(profile, env)
    profile_name = selected_profile or "default"
    credentials, credentials_error = _read_config(Path(
        env.get("AWS_SHARED_CREDENTIALS_FILE", str(Path.home() / ".aws" / "credentials"))
    ))
    config, config_error = _read_config(Path(
        env.get("AWS_CONFIG_FILE", str(Path.home() / ".aws" / "config"))
    ))
    section = "default" if profile_name == "default" else f"profile {profile_name}"
    configured = dict(config[section]) if config.has_section(section) else {}
    stored = dict(credentials[profile_name]) if credentials.has_section(profile_name) else {}
    profile_present = credentials.has_section(profile_name) or config.has_section(section)
    # Report booleans only. Never return or print keys, tokens, commands, or URLs.
    env_credentials = bool(env.get("AWS_ACCESS_KEY_ID") and env.get("AWS_SECRET_ACCESS_KEY"))
    file_credentials = bool(
        (stored.get("aws_access_key_id") and stored.get("aws_secret_access_key"))
        or (configured.get("aws_access_key_id") and configured.get("aws_secret_access_key"))
    )
    sso_configured = bool(configured.get("sso_session") or (
        configured.get("sso_start_url") and configured.get("sso_account_id")
        and configured.get("sso_role_name")
    ))
    process_configured = bool(configured.get("credential_process"))
    role_configured = bool(configured.get("role_arn") and (
        configured.get("source_profile") or configured.get("credential_source")
        or configured.get("web_identity_token_file")
    ))
    web_identity_configured = bool(selected_profile is None and env.get("AWS_ROLE_ARN") and env.get("AWS_WEB_IDENTITY_TOKEN_FILE"))
    container_configured = bool(
        env.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI") or env.get("AWS_CONTAINER_CREDENTIALS_FULL_URI")
    )
    # Passing an explicit/environment profile disables boto3's environment-key
    # provider; keep the local presence check consistent with that selection.
    configured_credentials = bool(
        (env_credentials and selected_profile is None) or file_credentials
        or sso_configured or process_configured or role_configured or web_identity_configured
        or container_configured
    )
    try:
        selected_region = resolve_region(region, env)
        region_error = None
    except BedrockConfigurationError as exc:
        selected_region = None
        region_error = exc.code
    return {
        "profile": profile_name,
        "profile_present": profile_present,
        "profile_error": "ProfileNotFound" if selected_profile is not None and not profile_present else None,
        "region": selected_region,
        "region_error": region_error,
        "profile_region_configured": bool(configured.get("region")),
        "environment_credentials_present": env_credentials,
        "profile_credentials_present": file_credentials,
        "sso_configured": sso_configured,
        "credential_process_configured": process_configured,
        "role_credentials_configured": role_configured,
        "web_identity_configured": web_identity_configured,
        "container_credentials_configured": container_configured,
        "credential_configuration_present": configured_credentials,
        "config_read_error": credentials_error or config_error,
        "credentials_validated": False,
        "network_calls": 0,
        "locally_ready": bool(
            selected_region and configured_credentials and not (credentials_error or config_error)
            and (selected_profile is None or profile_present)
        ),
    }


def make_bedrock_client(region: str, profile: str | None = None) -> Any:
    """Use the SDK credential chain; disable instance metadata by default."""
    import boto3
    from botocore.config import Config

    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client(
        "bedrock-runtime", region_name=region,
        config=Config(
            connect_timeout=CONNECT_TIMEOUT_SECONDS,
            read_timeout=READ_TIMEOUT_SECONDS,
            retries={"total_max_attempts": MAX_ATTEMPTS, "mode": "standard"},
        ),
    )


@dataclass(frozen=True)
class ConverseResult:
    text: str
    stop_reason: str
    latency_ms: float
    usage: dict[str, int]
    server_latency_ms: float | None = None


def invoke_converse(
    client: Any, model_id: str, user_text: str,
    system_prompt: str | None = None, max_tokens: int = 512,
) -> ConverseResult:
    request: dict[str, Any] = {
        "modelId": model_id,
        "messages": [{"role": "user", "content": [{"text": user_text}]}],
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0},
    }
    if system_prompt is not None:
        request["system"] = [{"text": system_prompt}]
    start = time.perf_counter()
    response = client.converse(**request)
    latency_ms = round((time.perf_counter() - start) * 1000, 3)
    if not isinstance(response, dict):
        raise BedrockResponseError("InvalidResponseEnvelope")
    output = response.get("output", {})
    message = output.get("message", {}) if isinstance(output, dict) else {}
    content = message.get("content", []) if isinstance(message, dict) else []
    raw_text = "".join(
        block["text"] for block in content
        if isinstance(block, dict) and isinstance(block.get("text"), str)
    ) if isinstance(content, list) else ""
    stop_reason = response.get("stopReason")
    safe_stop_reason = stop_reason if isinstance(stop_reason, str) and stop_reason in _STOP_REASONS else None
    if stop_reason != "end_turn":
        raise BedrockResponseError("IncompleteModelResponse", raw_text, safe_stop_reason)
    if not (
        isinstance(message, dict) and message.get("role") == "assistant"
        and isinstance(content, list) and content
        and all(isinstance(block, dict) and set(block) == {"text"}
                and isinstance(block["text"], str) for block in content)
        and raw_text.strip()
    ):
        raise BedrockResponseError("InvalidResponseContent", raw_text, safe_stop_reason)
    usage = response.get("usage", {})
    usage = {
        key: value for key, value in usage.items()
        if key in {"inputTokens", "outputTokens", "totalTokens", "cacheReadInputTokens", "cacheWriteInputTokens"}
        and type(value) is int and value >= 0
    } if isinstance(usage, dict) else {}
    metrics = response.get("metrics", {})
    server_latency = metrics.get("latencyMs") if isinstance(metrics, dict) else None
    if type(server_latency) not in (int, float) or not math.isfinite(server_latency) or server_latency < 0:
        server_latency = None
    return ConverseResult(raw_text, "end_turn", latency_ms, usage, server_latency)


def write_json_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
