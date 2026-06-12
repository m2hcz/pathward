"""Lexical and resolved path containment checks."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Union

from .errors import PathTraversalError, SymlinkEscapeError

StrPath = Union[str, "os.PathLike[str]"]


def _reject_absolute(raw: str) -> None:
    # PureWindowsPath catches drives ("C:"), drive-relative ("C:foo") and
    # UNC ("//server/share"); PurePosixPath catches rooted POSIX paths.
    normalized = raw.replace("\\", "/")
    if PureWindowsPath(raw).drive or PurePosixPath(normalized).is_absolute():
        raise PathTraversalError(
            f"absolute or drive-qualified path not allowed: {raw!r}", path=raw
        )


def safe_join(base: StrPath, *parts: StrPath) -> Path:
    """Join *parts* onto *base*, rejecting anything that could escape it.

    Purely lexical: no filesystem access. Rejects ``..`` segments, absolute
    paths, Windows drive/UNC prefixes and null bytes. Both ``/`` and ``\\``
    are treated as separators regardless of platform, so attacker-controlled
    names cannot smuggle separators past the check.
    """
    candidate = Path(base)
    for part in parts:
        raw = os.fspath(part)
        if "\x00" in raw:
            raise PathTraversalError(f"null byte in path component: {raw!r}", path=raw)
        _reject_absolute(raw)
        for piece in raw.replace("\\", "/").split("/"):
            if piece in ("", "."):
                continue
            if piece == "..":
                raise PathTraversalError(
                    f"parent-directory traversal detected: {raw!r}", path=raw
                )
            if PureWindowsPath(piece).drive:
                raise PathTraversalError(
                    f"drive-qualified component not allowed: {raw!r}", path=raw
                )
            candidate = candidate / piece
    return candidate


def is_within(base: StrPath, target: StrPath) -> bool:
    """Return True if *target* resolves to a location inside *base*.

    Both paths are fully resolved (symlinks followed), so a symlink that
    points outside *base* makes this return False.
    """
    base_resolved = Path(base).resolve()
    target_resolved = Path(target).resolve()
    return target_resolved == base_resolved or base_resolved in target_resolved.parents


def resolve_within(base: StrPath, *parts: StrPath) -> Path:
    """Safely join *parts* onto *base* and resolve the result.

    Combines the lexical checks of :func:`safe_join` with a post-resolution
    containment check, so symlinks inside the tree cannot redirect the final
    path outside *base*.

    Raises :class:`PathTraversalError` for lexical escapes and
    :class:`SymlinkEscapeError` when resolution leaves *base*.
    """
    base_resolved = Path(base).resolve()
    candidate = safe_join(base_resolved, *parts)
    resolved = candidate.resolve()
    if not (resolved == base_resolved or base_resolved in resolved.parents):
        raise SymlinkEscapeError(
            f"{candidate} resolves to {resolved}, outside {base_resolved}",
            path=str(candidate),
        )
    return resolved
