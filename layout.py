"""Layout utilities.

Paths, untouchable checks and tree helpers. Project-agnostic.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .contract import is_untouchable


def fingerprint_of(path: Path) -> str:
    """SHA-256 fingerprint of a file's contents."""
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def fingerprint_of_bytes(data: bytes) -> str:
    """SHA-256 fingerprint of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def safe_path(destiny: Path, relative: str) -> Path:
    """Resolve `relative` inside `destiny`, guarding against path escape."""
    clean = str(relative).replace("\\", "/").strip("/")
    parts = [p for p in clean.split("/") if p and p not in (".", "..")]
    result = destiny
    for part in parts:
        result = result / part
    return result


def list_python_files(root: Path) -> list[Path]:
    """All .py files under `root`, sorted."""
    return sorted(root.rglob("*.py"))
