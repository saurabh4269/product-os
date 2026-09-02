"""Model Armor screening — SDK when installed, REST fallback, deterministic needles always."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Literal

from loop.config import settings

ScreenKind = Literal["prompt", "response"]

_DETERMINISTIC_NEEDLES = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "system override",
    "disable model armor",
    "export_pii_table",
    "dump all customer",
    "exfiltrate",
    "send me the customer records",
    "access the production database",
)


def deterministic_screen(text: str) -> tuple[bool, str]:
    low = text.lower()
    for n in _DETERMINISTIC_NEEDLES:
        if n in low:
            return True, n
    return False, ""


def _project() -> str:
    return (os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()


def _region() -> str:
    return (os.environ.get("GOOGLE_CLOUD_REGION") or os.environ.get("LOOP_REGION") or "us-central1").strip()


def _template_id(kind: ScreenKind) -> str:
    if kind == "response":
        return (os.environ.get("LOOP_MODEL_ARMOR_RESPONSE_TEMPLATE") or "loop-response").strip()
    return (os.environ.get("LOOP_MODEL_ARMOR_PROMPT_TEMPLATE") or "loop-prompt").strip()


def _disabled() -> bool:
    return os.environ.get("LOOP_MODEL_ARMOR_DISABLE") == "1"


def _fail_closed() -> bool:
    return settings().model_armor_fail_closed and settings().block_on_screening_failure


def _template_path(kind: ScreenKind) -> str:
    project = _project()
    location = _region()
    template = _template_id(kind)
    return f"projects/{project}/locations/{location}/templates/{template}"


def _sdk_client() -> Any | None:
    if _disabled():
        return None
    try:
        from google.api_core import client_options as client_options_lib
        from google.cloud import modelarmor_v1

        region = _region()
        endpoint = f"modelarmor.{region}.rep.googleapis.com"
        opts = client_options_lib.ClientOptions(api_endpoint=endpoint)
        return modelarmor_v1.ModelArmorClient(client_options=opts)
    except ImportError:
        return None


def _sdk_match(resp: Any) -> str:
    try:
        from google.cloud.modelarmor_v1.types import FilterMatchState

        sr = getattr(resp, "sanitization_result", None)
        if sr is None:
            return ""
        if sr.filter_match_state == FilterMatchState.MATCH_FOUND:
            for name, fr in (sr.filter_results or {}).items():
                if getattr(fr, "match_state", None) == FilterMatchState.MATCH_FOUND:
                    return str(name)
            return "filter_match"
    except Exception:
        pass
    return ""


def _sdk_screen(text: str, *, kind: ScreenKind = "prompt") -> tuple[bool, str, str]:
    client = _sdk_client()
    if not client or not _project():
        return False, "", "sdk_unavailable"
    path = _template_path(kind)
    blob = text[:8000]
    try:
        if kind == "prompt":
            from google.cloud.modelarmor_v1.types import SanitizeUserPromptRequest

            req = SanitizeUserPromptRequest(name=path, user_prompt_data={"text": blob})
            resp = client.sanitize_user_prompt(request=req)
        else:
            from google.cloud.modelarmor_v1.types import SanitizeModelResponseRequest

            req = SanitizeModelResponseRequest(name=path, model_response_data={"text": blob})
            resp = client.sanitize_model_response(request=req)
        hit = _sdk_match(resp)
        if hit:
            return True, hit, "model_armor_sdk"
        return False, "", "model_armor_sdk"
    except Exception as exc:
        return False, "", f"sdk_error:{exc.__class__.__name__}"


def _rest_screen(text: str, *, kind: ScreenKind = "prompt") -> tuple[bool, str, str]:
    from loop import gcs_state

    project = _project()
    if not project or _disabled():
        return False, "", "disabled"
    token = gcs_state.metadata_access_token()
    if not token:
        if _fail_closed() and text.strip():
            return True, "screening_failure", "no_adc"
        return False, "", "no_adc"
    location = _region()
    template = _template_id(kind)
    parent = f"projects/{project}/locations/{location}/templates/{template}"
    method = "sanitizeUserPrompt" if kind == "prompt" else "sanitizeModelResponse"
    url = f"https://modelarmor.{location}.rep.googleapis.com/v1/{parent}:{method}"
    body = json.dumps(
        {"userPromptData": {"text": text[:8000]}}
        if kind == "prompt"
        else {"modelResponseData": {"text": text[:8000]}}
    ).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        if exc.code in {403, 404, 501}:
            if _fail_closed() and text.strip():
                return True, "screening_failure", f"api_{exc.code}"
            return False, "", f"api_{exc.code}"
        if _fail_closed():
            return True, "screening_failure", "api_error"
        return False, "", "api_error"
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        if _fail_closed() and text.strip():
            return True, "screening_failure", "api_unreachable"
        return False, "", "api_unreachable"

    block = _parse_armor_response(payload)
    if block:
        return True, block, "model_armor_rest"
    return False, "", "model_armor_rest"


def _parse_armor_response(payload: dict) -> str:
    for key in ("sanitizationResult", "filterResults", "piAndJailbreakFilterResult"):
        val = payload.get(key)
        if isinstance(val, dict):
            if val.get("matchState") == "MATCH_FOUND" or val.get("filterMatched"):
                return key
    filters = payload.get("filterResults")
    if isinstance(filters, list):
        for f in filters:
            if isinstance(f, dict) and f.get("matchState") == "MATCH_FOUND":
                return str(f.get("filterType") or "filter")
    return ""


def screen_text(text: str, *, kind: ScreenKind = "prompt") -> tuple[bool, str, str]:
    """Layered screen: SDK → REST → deterministic needles."""
    if not text or not str(text).strip():
        if _fail_closed():
            return True, "screening_failure", "empty"
        return False, "", "empty"
    blob = str(text)
    for fn in (_sdk_screen, _rest_screen):
        blocked, reason, backend = fn(blob, kind=kind)
        if blocked:
            return True, reason or "model_armor", backend
    hit, needle = deterministic_screen(blob)
    if hit:
        return True, needle, "deterministic"
    return False, "", "ok"


def screen_tool_output(text: str) -> tuple[bool, str, str]:
    return screen_text(text, kind="prompt")


def screen_model_response(text: str) -> tuple[bool, str, str]:
    return screen_text(text, kind="response")


def screen_chat(text: str) -> tuple[bool, str, str]:
    """Room chat and human-authored content — prompt template."""
    return screen_text(text, kind="prompt")
