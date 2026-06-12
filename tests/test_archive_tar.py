import io
import tarfile

import pytest

from pathward import UnsafeArchiveError, safe_extract, safe_extract_tar


def add_file(tf, name, data):
    payload = data.encode()
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    tf.addfile(info, io.BytesIO(payload))


def make_tar(path, entries):
    with tarfile.open(path, "w:gz") as tf:
        for name, data in entries:
            add_file(tf, name, data)
    return path


def test_extracts_files(tmp_path):
    archive = make_tar(tmp_path / "a.tar.gz", [("dir/hello.txt", "world")])
    dest = tmp_path / "out"
    safe_extract_tar(archive, dest)
    assert (dest / "dir" / "hello.txt").read_text() == "world"


def test_rejects_dotdot_member(tmp_path):
    archive = make_tar(tmp_path / "evil.tar.gz", [("../escape.txt", "pwned")])
    with pytest.raises(UnsafeArchiveError):
        safe_extract_tar(archive, tmp_path / "out")
    assert not (tmp_path / "escape.txt").exists()


def test_rejects_absolute_member(tmp_path):
    archive = make_tar(tmp_path / "evil.tar.gz", [("/etc/evil.txt", "pwned")])
    with pytest.raises(UnsafeArchiveError):
        safe_extract_tar(archive, tmp_path / "out")


def test_rejects_symlink_member(tmp_path):
    archive = tmp_path / "evil.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        info = tarfile.TarInfo("innocent.txt")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        tf.addfile(info)
    with pytest.raises(UnsafeArchiveError):
        safe_extract_tar(archive, tmp_path / "out")


def test_max_total_size_limit(tmp_path):
    archive = make_tar(tmp_path / "big.tar.gz", [("big.txt", "A" * 1000)])
    with pytest.raises(UnsafeArchiveError):
        safe_extract_tar(archive, tmp_path / "out", max_total_size=100)


def test_generic_safe_extract_dispatches_tar(tmp_path):
    archive = make_tar(tmp_path / "a.tar.gz", [("hello.txt", "world")])
    dest = tmp_path / "out"
    safe_extract(archive, dest)
    assert (dest / "hello.txt").read_text() == "world"
