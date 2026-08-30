"""Workspace user OAuth — ADK/GEAP pattern, hosted on this app.

One interactive consent (`access_type=offline`, `prompt=consent`) yields a
refresh token. We refresh in memory and call Gmail/Calendar APIs. Send stays
denied. Agent Identity / Gemini Enterprise injection is not used (plan-only).
"""

from __future__ import annotations

import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from loop.config import settings

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "mystical-timing-442601-q8")
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
HOSTED_URL = "https://loop-5uy6fkd7bq-uc.a.run.app"

SCOPES = (
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/userinfo.email",
)

CONSOLE_OVERVIEW = f"https://console.cloud.google.com/auth/overview?project={PROJECT}"
CONSOLE_CREATE_CLIENT = f"https://console.cloud.google.com/auth/clients/create?project={PROJECT}"
CONSOLE_AUDIENCE = f"https://console.cloud.google.com/auth/audience?project={PROJECT}"


def blob_path() -> Path:
    env = os.environ.get("LOOP_DATA_DIR")
    root = Path(env) if env else settings().data_dir
    return root / "workspace_oauth.json"


def _oauth_gcs_uri() -> str:
    explicit = (os.environ.get("LOOP_OAUTH_GCS_URI") or "").strip()
    if explicit:
        return explicit
    if os.environ.get("K_SERVICE"):
        project = os.environ.get("GOOGLE_CLOUD_PROJECT", PROJECT)
        return f"gs://{project}-loop-host/workspace_oauth.json"
    return ""


def _parse_gs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError("expected gs://bucket/object")
    rest = uri[5:]
    bucket, _, obj = rest.partition("/")
    if not bucket or not obj:
        raise ValueError("expected gs://bucket/object")
    return bucket, obj


def _metadata_access_token() -> str:
    try:
        req = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read()).get("access_token") or ""
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return ""


def _gcs_read_json() -> dict[str, Any]:
    uri = _oauth_gcs_uri()
    if not uri:
        return {}
    try:
        bucket, obj = _parse_gs_uri(uri)
    except ValueError:
        return {}
    token = _metadata_access_token()
    if not token:
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
        return {}
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return {}


def _gcs_write_json(data: dict[str, Any]) -> None:
    uri = _oauth_gcs_uri()
    if not uri or not data.get("refresh_token"):
        return
    try:
        bucket, obj = _parse_gs_uri(uri)
    except ValueError:
        return
    token = _metadata_access_token()
    if not token:
        return
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
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return


def _load() -> dict[str, Any]:
    path = blob_path()
    data: dict[str, Any] = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            data = {}
    if not data.get("refresh_token"):
        remote = _gcs_read_json()
        if remote.get("refresh_token"):
            data.update(remote)
    cid = (os.environ.get("LOOP_GOOGLE_OAUTH_CLIENT_ID") or "").strip()
    csec = (os.environ.get("LOOP_GOOGLE_OAUTH_CLIENT_SECRET") or "").strip()
    if cid and csec:
        data["client_id"] = cid
        data["client_secret"] = csec
    return data


def _save(data: dict[str, Any]) -> None:
    path = blob_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    _gcs_write_json(data)


def _http(method: str, url: str, body: dict | None = None, token: str = "") -> tuple[int, dict]:
    data = None if body is None else urllib.parse.urlencode(body).encode()
    headers = {"User-Agent": "product-os-loop", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"error": raw[:400]}
        return e.code, parsed
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return 0, {"error": str(e)}


def _json_http(method: str, url: str, body: dict | None = None, token: str = "") -> tuple[int, dict]:
    payload = None if body is None else json.dumps(body).encode()
    headers = {"User-Agent": "product-os-loop", "Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=payload, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"error": raw[:400]}
        return e.code, parsed
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return 0, {"error": str(e)}


def public_base(request_base: str = "") -> str:
    env = (os.environ.get("LOOP_PUBLIC_URL") or "").rstrip("/")
    if env:
        return env
    if os.environ.get("K_SERVICE"):
        return HOSTED_URL
    return (request_base or "http://127.0.0.1:8080").rstrip("/")


def redirect_uri(request_base: str = "") -> str:
    return public_base(request_base) + "/api/oauth/google/callback"


def console_return(ok: bool, detail: str = "") -> str:
    q = "workspace=ok" if ok else "workspace=error"
    if detail and not ok:
        q += "&detail=" + urllib.parse.quote(detail[:80])
    if os.environ.get("K_SERVICE"):
        return f"/connect?{q}"
    origin = os.environ.get("LOOP_CONSOLE_ORIGIN", "http://127.0.0.1:3000")
    if origin in {"", "*"}:
        return f"{HOSTED_URL}/connect?{q}"
    return origin.rstrip("/") + "/connect?" + q


def has_client(data: dict[str, Any] | None = None) -> bool:
    blob = data if data is not None else _load()
    return bool(blob.get("client_id") and blob.get("client_secret"))


def connected(data: dict[str, Any] | None = None) -> bool:
    blob = data if data is not None else _load()
    return bool(blob.get("refresh_token"))


def save_client(client_id: str, client_secret: str) -> dict[str, Any]:
    blob = _load()
    blob["client_id"] = _clean_client_id(client_id)
    blob["client_secret"] = (client_secret or "").strip().strip('"').strip("'")
    if not blob["client_id"] or not blob["client_secret"]:
        raise ValueError("client_id and client_secret required")
    if "apps.googleusercontent.com" not in blob["client_id"]:
        raise ValueError("client_id must look like ….apps.googleusercontent.com")
    _save(blob)
    return status()


def _clean_client_id(raw: str) -> str:
    """Strip common paste mistakes that cause Google invalid_client."""
    import re

    s = (raw or "").strip().strip('"').strip("'")
    s = re.sub(r"^https?://", "", s, flags=re.I).strip().strip("/")
    m = re.search(r"([0-9]+-[a-z0-9]+\.apps\.googleusercontent\.com)", s, re.I)
    return m.group(1) if m else s


def status(request_base: str = "") -> dict[str, Any]:
    blob = _load()
    ready = has_client(blob)
    return {
        "configured": ready,
        "connected": connected(blob),
        "email": blob.get("email") or "",
        "redirect_uri": redirect_uri(request_base),
        "scopes": list(SCOPES),
        "authorize_path": "/api/oauth/google/start",
        "authorize_url": public_base(request_base) + "/api/oauth/google/start",
        "console": {
            "overview": CONSOLE_OVERVIEW,
            "create_client": CONSOLE_CREATE_CLIENT,
            "audience": CONSOLE_AUDIENCE,
        },
    }


def authorization_url(request_base: str = "") -> str | None:
    blob = _load()
    if not has_client(blob):
        return None
    state = secrets.token_urlsafe(24)
    blob["pending_state"] = state
    blob["pending_at"] = time.time()
    _save(blob)
    params = {
        "client_id": blob["client_id"],
        "redirect_uri": redirect_uri(request_base),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def exchange_code(code: str, state: str, request_base: str = "") -> tuple[bool, str]:
    blob = _load()
    expected = blob.get("pending_state") or ""
    started = float(blob.get("pending_at") or 0)
    blob.pop("pending_state", None)
    blob.pop("pending_at", None)
    if not expected or state != expected or time.time() - started > 900:
        _save(blob)
        return False, "state"
    if not has_client(blob):
        return False, "client"
    status_code, payload = _http(
        "POST",
        TOKEN_URL,
        {
            "code": code,
            "client_id": blob["client_id"],
            "client_secret": blob["client_secret"],
            "redirect_uri": redirect_uri(request_base),
            "grant_type": "authorization_code",
        },
    )
    if status_code != 200 or not payload.get("refresh_token"):
        _save(blob)
        err = str(payload.get("error") or payload.get("error_description") or status_code)
        return False, err[:80]
    blob["refresh_token"] = payload["refresh_token"]
    blob["token"] = payload.get("access_token") or ""
    blob["expiry"] = time.time() + int(payload.get("expires_in") or 3500)
    if blob["token"]:
        _, info = _json_http("GET", USERINFO_URL, token=blob["token"])
        blob["email"] = info.get("email") or blob.get("email") or ""
    _save(blob)
    return True, blob.get("email") or ""


def access_token() -> str:
    legacy = (os.environ.get("LOOP_GMAIL_ACCESS_TOKEN") or os.environ.get("LOOP_CALENDAR_ACCESS_TOKEN") or "").strip()
    if legacy:
        return legacy
    blob = _load()
    token = blob.get("token") or ""
    expiry = float(blob.get("expiry") or 0)
    if token and time.time() < expiry - 60:
        return token
    refresh = blob.get("refresh_token") or ""
    if not refresh or not has_client(blob):
        return ""
    status_code, payload = _http(
        "POST",
        TOKEN_URL,
        {
            "refresh_token": refresh,
            "client_id": blob["client_id"],
            "client_secret": blob["client_secret"],
            "grant_type": "refresh_token",
        },
    )
    if status_code != 200 or not payload.get("access_token"):
        return ""
    blob["token"] = payload["access_token"]
    blob["expiry"] = time.time() + int(payload.get("expires_in") or 3500)
    if payload.get("refresh_token"):
        blob["refresh_token"] = payload["refresh_token"]
    _save(blob)
    return blob["token"]


def gmail_json(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    token = access_token()
    if not token:
        return 0, {"error": "no token"}
    return _json_http(method, "https://gmail.googleapis.com/gmail/v1/users/me" + path, body, token)


def calendar_json(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    token = access_token()
    if not token:
        return 0, {"error": "no token"}
    return _json_http(method, "https://www.googleapis.com/calendar/v3" + path, body, token)
