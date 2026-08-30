"""Gemini via Vertex AI (GCP billing / hackathon credits) or AI Studio API key."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from loop.config import default_model_id, generate_content_config_for


def use_vertex() -> bool:
    return os.environ.get("LOOP_USE_VERTEX") == "1" or os.environ.get("LOOP_VERTEX_GEMINI") == "1"


def _project() -> str:
    return (os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()


def _region() -> str:
    return (os.environ.get("GOOGLE_CLOUD_REGION") or "us-central1").strip()


def _api_key() -> str:
    return (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or "").strip()


def _access_token() -> str:
    from loop import gcs_state

    return gcs_state.metadata_access_token()


def gemini_configured() -> bool:
    if use_vertex():
        return bool(_project())
    return bool(_api_key())


def _extract_text(payload: dict[str, Any]) -> str:
    return (
        payload.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
        .strip()
    )


def _vertex_url(model: str) -> str:
    project = _project()
    region = _region()
    return (
        f"https://{region}-aiplatform.googleapis.com/v1/"
        f"projects/{project}/locations/{region}/publishers/google/models/{model}:generateContent"
    )


def _model_id() -> str:
    if use_vertex():
        return (os.environ.get("LOOP_VERTEX_MODEL") or "gemini-2.5-flash").strip()
    return default_model_id()


def generate_content(prompt: str, *, timeout: float = 90.0) -> str:
    """Generate text — Vertex when LOOP_USE_VERTEX=1, else AI Studio API key."""
    model = _model_id()
    body: dict[str, Any] = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    cfg = generate_content_config_for(model)
    if cfg:
        body["generationConfig"] = cfg

    if use_vertex():
        token = _access_token()
        if not token:
            raise RuntimeError("Vertex Gemini: no ADC token (need Cloud Run metadata or gcloud auth)")
        url = _vertex_url(model)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        res = httpx.post(url, json=body, headers=headers, timeout=timeout)
        if res.status_code >= 400:
            raise RuntimeError(f"Vertex Gemini {res.status_code}: {res.text[:300]}")
        return _extract_text(res.json())

    key = _api_key()
    if not key:
        raise RuntimeError("GOOGLE_API_KEY required when LOOP_USE_VERTEX is not set")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    res = httpx.post(url, params={"key": key}, json=body, timeout=timeout)
    if res.status_code >= 400:
        raise RuntimeError(f"Gemini API {res.status_code}: {res.text[:300]}")
    return _extract_text(res.json())


def generate_content_json(prompt: str, *, timeout: float = 90.0) -> dict[str, Any]:
    text = generate_content(prompt, timeout=timeout)
    blob = text.strip()
    if blob.startswith("```"):
        import re

        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", blob, re.S)
        if fence:
            blob = fence.group(1)
    start, end = blob.find("{"), blob.rfind("}")
    if start >= 0 and end > start:
        blob = blob[start : end + 1]
    return json.loads(blob)
