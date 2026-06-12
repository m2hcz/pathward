"""Symlink detection and TOCTOU-hardened file opening.

Inspired by the File Browser symlink disclosure, where symlinks planted
inside a served directory allowed reading arbitrary files on the host.
"""

from __future__ import annotations

import errno
import os
from pathlib import Path
from typing import IO, Any, Optional, Union

from .errors import FileChangedError, PathTraversalError, SymlinkEscapeError
from .resolve import safe_join

StrPath = Union[str, "os.PathLike[str]"]


def find_symlink(base: StrPath, path: StrPath) -> Optional[Path]:
    """Return the first symlink component between *base* and *path*.

    *path* may be absolute (must lie lexically under *base*) or relative to
    *base*. Returns ``None`` when no component is a symlink. Components that
    do not exist are simply not symlinks.
    """
    base_resolved = Path(base).resolve()
    p = Path(path)
    if not p.is_absolute():
        p = base_resolved / p
    p = Path(os.path.normpath(os.fspath(p)))
    try:
        rel = p.relative_to(base_resolved)
    except ValueError:
        raise PathTraversalError(
            f"{os.fspath(path)!r} is not under {base_resolved}", path=os.fspath(path)
        ) from None
    current = base_resolved
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            return current
    return None


def contains_symlink(base: StrPath, path: StrPath) -> bool:
    """True if any component of *path* below *base* is a symlink."""
    return find_symlink(base, path) is not None


def assert_no_symlinks(base: StrPath, path: StrPath) -> None:
    """Raise :class:`SymlinkEscapeError` if *path* crosses any symlink."""
    link = find_symlink(base, path)
    if link is not None:
        raise SymlinkEscapeError(f"symlink component found: {link}", path=str(link))


def safe_open(
    base: StrPath,
    *parts: StrPath,
    mode: str = "r",
    follow_symlinks: bool = False,
    **open_kwargs: Any,
) -> IO[Any]:
    """Open ``base/parts...`` ensuring the file stays inside *base*.

    With ``follow_symlinks=False`` (default) any symlink component is
    rejected, the final component is opened with ``O_NOFOLLOW`` where
    available, and the opened descriptor is cross-checked against the path
    (`fstat` vs `lstat`) to detect files swapped during the race window.

    With ``follow_symlinks=True`` symlinks are allowed as long as the fully
    resolved target still lives inside *base*.
    """
    base_resolved = Path(base).resolve()
    candidate = safe_join(base_resolved, *parts)

    if follow_symlinks:
        target = candidate.resolve()
        if not (target == base_resolved or base_resolved in target.parents):
            raise SymlinkEscapeError(
                f"{candidate} resolves to {target}, outside {base_resolved}",
                path=str(candidate),
            )
    else:
        assert_no_symlinks(base_resolved, candidate)
        target = candidate

    def _opener(path: str, flags: int) -> int:
        if not follow_symlinks:
            flags |= getattr(os, "O_NOFOLLOW", 0)
        return os.open(path, flags)

    try:
        fobj = open(target, mode, opener=_opener, **open_kwargs)
    except OSError as exc:
        if exc.errno == getattr(errno, "ELOOP", None):
            raise SymlinkEscapeError(
                f"symlink appeared at {target} during open", path=str(target)
            ) from exc
        raise

    if not follow_symlinks:
        try:
            st_fd = os.fstat(fobj.fileno())
            st_path = os.lstat(target)
            if (st_fd.st_dev, st_fd.st_ino) != (st_path.st_dev, st_path.st_ino):
                raise FileChangedError(
                    f"{target} changed between validation and open "
                    "(possible TOCTOU attack)"
                )
        except BaseException:
            fobj.close()
            raise
    return fobj
