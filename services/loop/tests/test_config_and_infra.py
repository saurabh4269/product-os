from __future__ import annotations

from pathlib import Path

import yaml

from loop.agents.apps import ALL_AGENT_NAMES
from loop.config import (
    default_model_id,
    generate_content_config_for,
    load_models,
    silently_ignored_sampling_models,
)

ROOT = Path(__file__).resolve().parents[3]


def test_default_model_is_35_flash():
    assert default_model_id() == "gemini-3.5-flash"
    models = load_models()
    assert models.default_reasoning.lifecycle_tier == "twelve_month"
    assert generate_content_config_for("gemini-3.5-flash") is not None
    for mid in silently_ignored_sampling_models():
        assert generate_content_config_for(mid) is None
    assert "gemini-3.6-flash" in silently_ignored_sampling_models()
    assert "gemini-3.5-flash-lite" in silently_ignored_sampling_models()


def test_no_inline_sampling_on_ignored_models():
    """P-6b: sampling params must not be set for 3.6-flash / 3.5-flash-lite."""
    banned = ("gemini-3.6-flash", "gemini-3.5-flash-lite")
    haystack = []
    for path in (ROOT / "services" / "loop").rglob("*.py"):
        haystack.append(path.read_text())
    blob = "\n".join(haystack)
    for mid in banned:
        if mid not in blob:
            continue
        # Allowed in config loader tests and yaml comments; not as generate_content_config targets.
        assert "GenerateContentConfig" not in blob.split(mid)[0][-200:]


def test_roster_agents_named():
    assert len(ALL_AGENT_NAMES) == 23


def test_failopen_false_in_terraform():
    """M-5a: failOpen must be pinned false; CI fails if true or missing on Armor extensions."""
    cheap = (ROOT / "infra" / "terraform" / "cheap").rglob("*.tf")
    gated = (ROOT / "infra" / "terraform" / "gated").rglob("*.tf")
    files = list(cheap) + list(gated)
    assert files, "terraform must exist"
    blob = "\n".join(p.read_text() for p in files)
    assert "fail_open = true" not in blob
    assert "failOpen = true" not in blob
    assert "CONTENT_AUTHZ" in blob
    assert "google_network_services_authz_extension" in blob
    assert "fail_open = false" in blob or "failOpen = false" in blob


def test_deploy_gcp_loop_host_profile():
    """Hosted LOOP: 4Gi RAM, lean boot (no apt-get curl/git/node — python urllib fetches the bundle)."""
    script = (ROOT / "scripts" / "deploy-gcp.sh").read_text()
    assert "--memory 4Gi" in script
    assert "--memory 2Gi" not in script
    assert "expected Cloud Run memory 4Gi" in script
    assert "DEPLOYED_MEMORY" in script
    assert "apt-get" not in script
    assert "urlretrieve" in script
    assert "/tmp/loop.tgz" in script
    assert "^|^-c|" in script
    # One-arg urlretrieve writes a random NamedTemporaryFile (Py 3.12); tar would miss it.
    assert "cd /tmp && python -c" not in script
    assert "nodejs" not in script
    assert "npm" not in script
    assert "python3-pip" not in script
    assert "/api/internal/state/persist" in script


def test_deploy_gcp_actions_invokes_script():
    workflow = (ROOT / ".github" / "workflows" / "deploy-gcp.yml").read_text()
    assert "./scripts/deploy-gcp.sh" in workflow
    assert "2Gi" not in workflow


def test_models_yaml_forbids_pro():
    raw = yaml.safe_load((ROOT / "config" / "models.yaml").read_text())
    assert "gemini-3.5-pro" in raw["forbidden"]
