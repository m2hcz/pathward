import pytest

from pathward import (
    PathTraversalError,
    SymlinkEscapeError,
    assert_no_symlinks,
    contains_symlink,
    find_symlink,
)

from helpers import requires_symlinks


def test_no_symlink_in_clean_tree(tmp_path):
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "file.txt").write_text("data")
    assert not contains_symlink(tmp_path, "a/b/file.txt")


@requires_symlinks
def test_detects_symlink_final_component(tmp_path):
    real = tmp_path / "real.txt"
    real.write_text("data")
    (tmp_path / "link.txt").symlink_to(real)
    assert contains_symlink(tmp_path, "link.txt")


@requires_symlinks
def test_detects_symlink_intermediate_dir(tmp_path):
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    (real_dir / "file.txt").write_text("data")
    (tmp_path / "link_dir").symlink_to(real_dir, target_is_directory=True)
    assert contains_symlink(tmp_path, "link_dir/file.txt")


@requires_symlinks
def test_find_symlink_returns_path(tmp_path):
    real = tmp_path / "real.txt"
    real.write_text("data")
    link = tmp_path / "link.txt"
    link.symlink_to(real)
    assert find_symlink(tmp_path, "link.txt") == link


def test_assert_no_symlinks_passes(tmp_path):
    (tmp_path / "plain.txt").write_text("data")
    assert_no_symlinks(tmp_path, "plain.txt")


@requires_symlinks
def test_assert_no_symlinks_raises(tmp_path):
    real = tmp_path / "real.txt"
    real.write_text("data")
    (tmp_path / "link.txt").symlink_to(real)
    with pytest.raises(SymlinkEscapeError):
        assert_no_symlinks(tmp_path, "link.txt")


def test_path_outside_base_raises(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    with pytest.raises(PathTraversalError):
        contains_symlink(base, tmp_path / "outside.txt")
