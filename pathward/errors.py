"""Exception hierarchy for pathward.

All exceptions raised by this library derive from :class:`PathwardError`,
so callers can catch a single base class at trust boundaries.
"""

from __future__ import annotations

from typing import Optional


class PathwardError(Exception):
    """Base class for every error raised by pathward."""


class PathTraversalError(PathwardError, ValueError):
    """A path component tried to escape the base directory lexically.

    Raised for ``..`` segments, absolute paths, drive letters, UNC paths
    and null bytes. Also a :class:`ValueError` for ergonomic catching.
    """

    def __init__(self, message: str, *, path: Optional[str] = None) -> None:
        super().__init__(message)
        self.path = path


class SymlinkEscapeError(PathwardError):
    """A symlink would lead (or leads) outside the allowed base directory."""

    def __init__(self, message: str, *, path: Optional[str] = None) -> None:
        super().__init__(message)
        self.path = path


class UnsafeArchiveError(PathwardError):
    """An archive member is unsafe to extract (Zip Slip, links, bombs)."""

    def __init__(self, message: str, *, member: Optional[str] = None) -> None:
        super().__init__(message)
        self.member = member


class FileChangedError(PathwardError):
    """The file changed between validation and use (possible TOCTOU attack)."""
