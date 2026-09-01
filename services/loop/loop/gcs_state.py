"""Persist small JSON blobs on GCS (Cloud Run ephemeral disk backup)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "mystical-timing-442601-q8")
_last_error: str = ""


def last_error() -> str:
    return _last_error


def _set_error(msg: str) -> None:
    global _last_error
    _last_error = msg[:400]


def gcs_uri(env_key: str, default_object: str) -> str:
    explicit = (os.environ.get(env_key) or "").strip()
    if explicit:
        return explicit
    if os.environ.get("K_SERVICE"):
        return f"gs://{PROJECT}-loop-host/{default_object}"
    return ""


def parse_gs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError("expected gs://bucket/object")
    rest = uri[5:]
    bucket, _, obj = rest.partition("/")
    if not bucket or not obj:
        raise ValueError("expected gs://bucket/object")
    return bucket, obj


def metadata_access_token() -> str:
    try:
        req = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read()).get("access_token") or ""
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return ""


def read_json(uri: str) -> dict[str, Any]:
    if not uri:
        return {}
    try:
        bucket, obj = parse_gs_uri(uri)
    except ValueError as exc:
        _set_error(str(exc))
        return {}
    token = metadata_access_token()
    if not token:
        _set_error("no metadata token for GCS read")
        return {}
    quoted = urllib.parse.quote(obj, safe="")
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{quoted}?alt=media"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}
        _set_error(f"GCS read {e.code}: {e.read().decode()[:120]}")
        return {}
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        _set_error(f"GCS read failed: {exc}")
        return {}


def object_metadata(uri: str) -> dict[str, Any]:
    if not uri:
        return {}
    try:
        bucket, obj = parse_gs_uri(uri)
    except ValueError:
        return {}
    token = metadata_access_token()
    if not token:
        return {}
    quoted = urllib.parse.quote(obj, safe="")
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{quoted}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        return {}


def write_json(uri: str, data: dict[str, Any]) -> bool:
    if not uri or not data:
        return False
    try:
        bucket, obj = parse_gs_uri(uri)
    except ValueError as exc:
        _set_error(str(exc))
        return False
    token = metadata_access_token()
    if not token:
        _set_error("no metadata token for GCS write")
        return False
    payload = json.dumps(data, indent=2).encode()
    quoted = urllib.parse.quote(obj, safe="")
    url = (
        f"https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o"
        f"?uploadType=media&name={quoted}"
    )
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=15)
        _set_error("")
        return True
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        _set_error(f"GCS write failed: {exc}")
        return False


def read_bytes(uri: str) -> bytes:
    if not uri:
        return b""
    try:
        bucket, obj = parse_gs_uri(uri)
    except ValueError:
        return b""
    token = metadata_access_token()
    if not token:
        return b""
    quoted = urllib.parse.quote(obj, safe="")
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{quoted}?alt=media"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return b""
        return b""
    except (OSError, urllib.error.URLError, TimeoutError):
        return b""


def write_bytes(uri: str, payload: bytes, *, content_type: str = "application/octet-stream") -> bool:
    if not uri or not payload:
        return False
    try:
        bucket, obj = parse_gs_uri(uri)
    except ValueError:
        return False
    token = metadata_access_token()
    if not token:
        return False
    quoted = urllib.parse.quote(obj, safe="")
    url = (
        f"https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o"
        f"?uploadType=media&name={quoted}"
    )
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": content_type,
        },
    )
    try:
        urllib.request.urlopen(req, timeout=60)
        _set_error("")
        return True
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        _set_error(f"GCS write_bytes failed: {exc}")
        return False
