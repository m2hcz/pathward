"""Zip Slip-safe archive extraction for zip and tar files."""

from __future__ import annotations

import contextlib
import shutil
import stat
import tarfile
import zipfile
from pathlib import Path
from typing import List, Optional, Union

from .errors import PathTraversalError, UnsafeArchiveError
from .resolve import safe_join

ZipSource = Union[str, "Path", zipfile.ZipFile]
TarSource = Union[str, "Path", tarfile.TarFile]


def _member_target(dest: Path, name: str) -> Path:
    try:
        return safe_join(dest, name)
    except PathTraversalError as exc:
        raise UnsafeArchiveError(
            f"unsafe member name {name!r}: {exc}", member=name
        ) from exc


def safe_extract_zip(
    src: ZipSource,
    dest: Union[str, Path],
    *,
    max_members: Optional[int] = None,
    max_total_size: Optional[int] = None,
) -> List[Path]:
    """Extract a zip archive into *dest*, refusing unsafe members.

    Rejects members whose names escape *dest* (Zip Slip), symlink members,
    and archives exceeding *max_members* or *max_total_size* (uncompressed
    bytes). Returns the list of extracted file paths.
    """
    dest_path = Path(dest)
    dest_path.mkdir(parents=True, exist_ok=True)
    extracted: List[Path] = []
    with contextlib.ExitStack() as stack:
        if isinstance(src, zipfile.ZipFile):
            zf = src
        else:
            zf = stack.enter_context(zipfile.ZipFile(src))
        infos = zf.infolist()
        if max_members is not None and len(infos) > max_members:
            raise UnsafeArchiveError(
                f"archive has {len(infos)} members, limit is {max_members}"
            )
        if max_total_size is not None:
            total = sum(info.file_size for info in infos)
            if total > max_total_size:
                raise UnsafeArchiveError(
                    f"archive expands to {total} bytes, limit is {max_total_size}"
                )
        for info in infos:
            name = info.filename
            if stat.S_ISLNK(info.external_attr >> 16):
                raise UnsafeArchiveError(
                    f"symlink member not allowed: {name!r}", member=name
                )
            target = _member_target(dest_path, name)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src_f, open(target, "wb") as dst_f:
                shutil.copyfileobj(src_f, dst_f)
            extracted.append(target)
    return extracted


def safe_extract_tar(
    src: TarSource,
    dest: Union[str, Path],
    *,
    max_members: Optional[int] = None,
    max_total_size: Optional[int] = None,
) -> List[Path]:
    """Extract a tar archive into *dest*, refusing unsafe members.

    Rejects members whose names escape *dest*, symlink/hardlink members and
    device nodes, plus archives exceeding *max_members* or *max_total_size*.
    File metadata (permissions, owners, mtimes) is deliberately not
    preserved. Returns the list of extracted file paths.
    """
    dest_path = Path(dest)
    dest_path.mkdir(parents=True, exist_ok=True)
    extracted: List[Path] = []
    with contextlib.ExitStack() as stack:
        if isinstance(src, tarfile.TarFile):
            tf = src
        else:
            tf = stack.enter_context(tarfile.open(src))
        members = tf.getmembers()
        if max_members is not None and len(members) > max_members:
            raise UnsafeArchiveError(
                f"archive has {len(members)} members, limit is {max_members}"
            )
        if max_total_size is not None:
            total = sum(member.size for member in members)
            if total > max_total_size:
                raise UnsafeArchiveError(
                    f"archive expands to {total} bytes, limit is {max_total_size}"
                )
        for member in members:
            name = member.name
            if member.issym() or member.islnk():
                raise UnsafeArchiveError(
                    f"link member not allowed: {name!r}", member=name
                )
            if member.isdev():
                raise UnsafeArchiveError(
                    f"device member not allowed: {name!r}", member=name
                )
            target = _member_target(dest_path, name)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            src_f = tf.extractfile(member)
            if src_f is None:  # pragma: no cover - defensive
                continue
            with src_f, open(target, "wb") as dst_f:
                shutil.copyfileobj(src_f, dst_f)
            extracted.append(target)
    return extracted


def safe_extract(
    src: Union[str, Path],
    dest: Union[str, Path],
    *,
    max_members: Optional[int] = None,
    max_total_size: Optional[int] = None,
) -> List[Path]:
    """Extract a zip or tar archive (auto-detected) safely into *dest*."""
    src_str = str(src)
    if zipfile.is_zipfile(src_str):
        return safe_extract_zip(
            src_str, dest, max_members=max_members, max_total_size=max_total_size
        )
    if tarfile.is_tarfile(src_str):
        return safe_extract_tar(
            src_str, dest, max_members=max_members, max_total_size=max_total_size
        )
    raise UnsafeArchiveError(f"unrecognized archive format: {src_str!r}")
