"""Open a PR on the tenant repo when a token exists. Never merge."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4

from loop.tenant import ConnectorReport, Tenant


def _token() -> str:
    for key in ("LOOP_GITHUB_TOKEN", "GITHUB_TOKEN"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    gh = shutil.which("gh")
    if not gh:
        return ""
    try:
        out = subprocess.run(
            [gh, "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return (out.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _request(method: str, url: str, token: str, body: dict | None = None) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "product-os-loop",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode() or "{}"
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:500]
        try:
            parsed = json.loads(detail)
        except json.JSONDecodeError:
            parsed = {"error": detail}
        return e.code, parsed


def _put_file(repo: str, token: str, branch: str, path: str, content: str, message: str) -> tuple[int, dict]:
    encoded = urllib.parse.quote(path, safe="/")
    st, existing = _request(
        "GET",
        f"https://api.github.com/repos/{repo}/contents/{encoded}?ref={urllib.parse.quote(branch)}",
        token,
    )
    payload: dict = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "branch": branch,
    }
    if st == 200 and existing.get("sha"):
        payload["sha"] = existing["sha"]
    return _request("PUT", f"https://api.github.com/repos/{repo}/contents/{encoded}", token, payload)


def open_pr(
    tenant: Tenant,
    title: str,
    body: str,
    *,
    file_path: str = "",
    file_content: str = "",
    branch: str | None = None,
) -> ConnectorReport:
    token = _token()
    if not token or not tenant.repo:
        return ConnectorReport(
            status="skipped",
            connector="github.pr",
            detail="no LOOP_GITHUB_TOKEN/GITHUB_TOKEN/gh auth or tenant.repo",
        )
    repo = tenant.repo.strip()
    st, meta = _request("GET", f"https://api.github.com/repos/{repo}", token)
    if st != 200:
        return ConnectorReport(status="skipped", connector="github.pr", detail=f"repo {st}: {meta}")
    base = meta.get("default_branch") or "main"
    st, ref = _request("GET", f"https://api.github.com/repos/{repo}/git/ref/heads/{base}", token)
    if st != 200:
        return ConnectorReport(status="skipped", connector="github.pr", detail=f"ref {st}: {ref}")
    sha = (ref.get("object") or {}).get("sha")
    if not sha:
        return ConnectorReport(status="skipped", connector="github.pr", detail="no base sha")
    head = branch or f"loop/{uuid4().hex[:10]}"
    st, created = _request(
        "POST",
        f"https://api.github.com/repos/{repo}/git/refs",
        token,
        {"ref": f"refs/heads/{head}", "sha": sha},
    )
    if st not in {200, 201}:
        return ConnectorReport(status="skipped", connector="github.pr", detail=f"branch {st}: {created}")
    path = file_path or "config/flags.json"
    content = file_content or f"# Product OS change\n\n{title}\n\n{body}\n"
    st, put = _put_file(repo, token, head, path, content, title)
    if st not in {200, 201}:
        return ConnectorReport(status="skipped", connector="github.pr", detail=f"commit {st}: {put}")
    st, pr = _request(
        "POST",
        f"https://api.github.com/repos/{repo}/pulls",
        token,
        {
            "title": title,
            "body": body + "\n\nProduct OS does not merge this. A human must merge. OS never production-deploys the tenant app.",
            "head": head,
            "base": base,
        },
    )
    url = pr.get("html_url")
    if st in {200, 201} and url:
        return ConnectorReport(status="applied", connector="github.pr", detail="pull request opened", url=str(url))
    return ConnectorReport(status="skipped", connector="github.pr", detail=f"pull {st}: {pr}")


def create_issue(tenant: Tenant, title: str, body: str) -> ConnectorReport:
    token = _token()
    if not token or not tenant.repo:
        return ConnectorReport(
            status="skipped",
            connector="github.issue",
            detail="no LOOP_GITHUB_TOKEN/GITHUB_TOKEN/gh auth or tenant.repo",
        )
    st, payload = _request(
        "POST",
        f"https://api.github.com/repos/{tenant.repo}/issues",
        token,
        {"title": title, "body": body},
    )
    if st in {200, 201} and payload.get("html_url"):
        return ConnectorReport(
            status="applied",
            connector="github.issue",
            detail="issue opened",
            url=str(payload["html_url"]),
        )
    return ConnectorReport(status="skipped", connector="github.issue", detail=f"github {st}: {payload}")
