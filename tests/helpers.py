"""Shared test helpers."""

import tempfile
from pathlib import Path

import pytest


def _symlinks_supported() -> bool:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "target.txt"
        target.write_text("x")
        try:
            (Path(td) / "link").symlink_to(target)
        except (OSError, NotImplementedError):
            return False
    return True


SYMLINKS_SUPPORTED = _symlinks_supported()

requires_symlinks = pytest.mark.skipif(
    not SYMLINKS_SUPPORTED,
    reason="symlinks not supported (on Windows, requires admin or Developer Mode)",
)
