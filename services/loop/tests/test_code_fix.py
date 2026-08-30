"""Code fix patch generation."""

from __future__ import annotations

from loop.code_fix import _deterministic_safari_patch, _expand_files, resolve_brief


def test_expand_files_maps_payment_paths():
    out = _expand_files(["payment/3ds.ts", "src/lib/loop.ts"])
    assert "src/app/(store)/checkout/page.tsx" in out
    assert "src/lib/loop.ts" in out


def test_deterministic_patch_adds_regression_test():
    brief = {"issue": "Safari 3DS hang", "hypothesis": "callback timeout", "fixture_id": "safari_3ds"}
    files = {
        "src/app/(store)/checkout/page.tsx": 'await new Promise((r) => setTimeout(r, 2200))\n',
        "src/lib/loop.ts": 'return flags.pay_sdk_4_3 === "on" || flags.pay_sdk === "4.3.0"\n',
    }
    patched = _deterministic_safari_patch(brief, files)
    assert "tests/regression/safari-3ds-checkout.test.ts" in patched
    assert "800" in patched["src/app/(store)/checkout/page.tsx"]
    assert "4.2.1" in patched["src/lib/loop.ts"]


def test_resolve_brief_from_action_artifacts():
    class A:
        artifacts = {"code_brief": {"issue": "x", "likely_files": ["a.ts"]}}

    class I:
        room_id = None

    class S:
        def list_messages(self, _):
            return []

    assert resolve_brief(A(), I(), S())["issue"] == "x"
