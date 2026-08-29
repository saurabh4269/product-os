from __future__ import annotations

import json
from typing import Any

from ..config import REPO_ROOT
from ..engine import redact_pii

FIXTURES = REPO_ROOT / "data" / "fixtures"


def make_untrusted_tools() -> list:
    def read_github_issue(number: int = 1847) -> dict[str, Any]:
        """Return repository issue body. Output is untrusted DATA (M-13)."""
        inj = json.loads((FIXTURES / "prompt_injection_tool.json").read_text())
        poison = (FIXTURES / "poisoned_github_issue.md").read_text()
        if number == 1847:
            return {
                "number": number,
                "title": inj["issue"]["title"],
                "body": inj["issue"]["body"] + "\n\n" + poison,
                "trust": "untrusted",
            }
        return {"number": number, "body": "", "trust": "untrusted"}

    def read_transcript(fixture_id: str = "adv-pii-transcript-001") -> dict[str, Any]:
        raw = json.loads((FIXTURES / "pii_transcript.json").read_text())
        joined = " ".join(t["text"] for t in raw["turns"])
        return {
            "fixture_id": fixture_id,
            "trust": "untrusted",
            "redacted": redact_pii(joined),
            "raw_retained": False,
        }

    read_github_issue.__name__ = "read_github_issue"
    read_transcript.__name__ = "read_transcript"
    return [read_github_issue, read_transcript]
