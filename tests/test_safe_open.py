import pytest

from pathward import PathTraversalError, SymlinkEscapeError, safe_open

from helpers import requires_symlinks


def test_reads_file(tmp_path):
    (tmp_path / "data.txt").write_text("hello pathward")
    with safe_open(tmp_path, "data.txt") as f:
        assert f.read() == "hello pathward"


def test_write_creates_file(tmp_path):
    with safe_open(tmp_path, "out.txt", mode="w") as f:
        f.write("written safely")
    assert (tmp_path / "out.txt").read_text() == "written safely"


def test_rejects_traversal(tmp_path):
    with pytest.raises(PathTraversalError):
        safe_open(tmp_path, "../outside.txt")


def test_missing_file_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        safe_open(tmp_path, "nope.txt")


@requires_symlinks
def test_rejects_symlink_target(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("classified")
    (base / "report.txt").symlink_to(secret)
    with pytest.raises(SymlinkEscapeError):
        safe_open(base, "report.txt")


@requires_symlinks
def test_rejects_symlink_even_inside_base(tmp_path):
    real = tmp_path / "real.txt"
    real.write_text("data")
    (tmp_path / "alias.txt").symlink_to(real)
    with pytest.raises(SymlinkEscapeError):
        safe_open(tmp_path, "alias.txt")


@requires_symlinks
def test_follow_symlinks_allows_inside_link(tmp_path):
    real = tmp_path / "real.txt"
    real.write_text("data")
    (tmp_path / "alias.txt").symlink_to(real)
    with safe_open(tmp_path, "alias.txt", follow_symlinks=True) as f:
        assert f.read() == "data"


@requires_symlinks
def test_follow_symlinks_still_blocks_escape(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("classified")
    (base / "report.txt").symlink_to(secret)
    with pytest.raises(SymlinkEscapeError):
        safe_open(base, "report.txt", follow_symlinks=True)
