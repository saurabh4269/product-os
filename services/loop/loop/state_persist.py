"""Full SQLite backup on GCS — investigations survive Cloud Run deploy."""

from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path

from loop import gcs_state

_lock = threading.Lock()
_timer: threading.Timer | None = None
_last_upload = 0.0


def state_gcs_uri() -> str:
    return gcs_state.gcs_uri("LOOP_STATE_GCS_URI", "loop_state.db")


def hydrate_db(local_path: Path) -> bool:
    """Restore SQLite from GCS when blob exists and local file is missing or empty."""
    uri = state_gcs_uri()
    if not uri:
        return False
    blob = gcs_state.read_bytes(uri)
    if len(blob) < 512:
        return False
    local_path.parent.mkdir(parents=True, exist_ok=True)
    if local_path.exists() and local_path.stat().st_size >= len(blob):
        return False
    tmp = local_path.with_suffix(".db.restore")
    tmp.write_bytes(blob)
    tmp.replace(local_path)
    return True


def persist_db(local_path: Path) -> bool:
    uri = state_gcs_uri()
    if not uri or not local_path.is_file():
        return False
    # Checkpoint WAL so upload is consistent.
    try:
        import sqlite3

        conn = sqlite3.connect(str(local_path))
        conn.execute("PRAGMA wal_checkpoint(FULL)")
        conn.close()
    except sqlite3.Error:
        pass
    return gcs_state.write_bytes(uri, local_path.read_bytes(), content_type="application/x-sqlite3")


def schedule_snapshot(local_path: Path, delay_s: float = 2.0) -> None:
    global _timer

    def fire() -> None:
        global _last_upload
        with _lock:
            if not local_path.is_file():
                return
            if persist_db(local_path):
                _last_upload = time.time()

    with _lock:
        if _timer:
            _timer.cancel()
        _timer = threading.Timer(delay_s, fire)
        _timer.daemon = True
        _timer.start()


def copy_local_backup(local_path: Path, dest_dir: Path) -> Path | None:
    """Dev helper: copy db to dest_dir for inspection."""
    if not local_path.is_file():
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / local_path.name
    shutil.copy2(local_path, out)
    return out
