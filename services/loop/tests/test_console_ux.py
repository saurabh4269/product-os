"""Console UX invariants — unauth shell, rooms index, SPA routing."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from loop import api as api_mod

ROOT = Path(__file__).resolve().parents[3]
CONSOLE = ROOT / "apps" / "console"


def test_rooms_index_does_not_auto_redirect():
    src = (CONSOLE / "app" / "rooms" / "page.tsx").read_text()
    assert "router.replace" not in src
    assert "router.push" not in src
    assert "tryGet" in src
    assert "ConnectAdminCta" in src
    assert "adminAuthRequired" in src


def test_rooms_index_401_uses_connect_not_error_state():
    src = (CONSOLE / "app" / "rooms" / "page.tsx").read_text()
    assert "ConnectAdminCta" in src
    assert "adminAuthRequired" in src
    err_block = src[src.index("if (err)") : src.index("const desks")]
    assert "adminAuthRequired" not in err_block
    assert "{adminAuthRequired ?" in src


def test_room_view_401_uses_connect_not_error_state():
    src = (CONSOLE / "components" / "room-view.tsx").read_text()
    assert "isAdminAuthError" in src
    assert "ConnectAdminCta" in src
    assert "adminAuthRequired" in src
    assert src.index("adminAuthRequired") < src.index('if (err) return <ErrorState')


def test_home_uses_try_config_for_public_shell():
    src = (CONSOLE / "app" / "page.tsx").read_text()
    assert "tryConfig" in src
    assert "tryGet" in src
    assert "ConnectAdminCta" in src


def test_try_config_helper_retries_and_defaults():
    api_src = (CONSOLE / "lib" / "api.ts").read_text()
    assert "export async function tryConfig" in api_src
    assert "DEFAULT_PUBLIC_CONFIG" in api_src


def test_package_host_duplicates_rooms_index():
    script = (ROOT / "scripts" / "package-host.sh").read_text()
    assert "rooms/index.html" in script
    assert "rooms.html" in script


def test_spa_rooms_path_prefers_index_not_placeholder(tmp_path, monkeypatch):
    static = tmp_path / "static"
    rooms_dir = static / "rooms"
    rooms_dir.mkdir(parents=True)
    (static / "rooms.html").write_text("<html>rooms-index</html>", encoding="utf-8")
    (rooms_dir / "index.html").write_text("<html>rooms-index</html>", encoding="utf-8")
    (rooms_dir / "_").mkdir()
    (rooms_dir / "_" / "index.html").write_text("<html>room-detail</html>", encoding="utf-8")

    monkeypatch.setattr(api_mod, "_STATIC", static)

    for path in ("rooms", "rooms/"):
        page = api_mod._spa_file(path)
        assert page is not None
        assert "rooms-index" in page.path.read_text(encoding="utf-8")

    detail = api_mod._spa_file("rooms/room_abc123")
    assert detail is not None
    assert "room-detail" in detail.path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", ["/api/config"])
def test_public_config_no_admin(prod_client, path):
    assert prod_client.get(path).status_code == 200


@pytest.fixture()
def prod_client(engine, monkeypatch):
    monkeypatch.setenv("LOOP_EVAL", "0")
    monkeypatch.setenv("LOOP_ADMIN_TOKEN", "secret")
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        yield client
