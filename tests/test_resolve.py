import pytest

from pathward import (
    PathTraversalError,
    SymlinkEscapeError,
    is_within,
    resolve_within,
)

from helpers import requires_symlinks


def test_is_within_child(tmp_path):
    child = tmp_path / "sub" / "file.txt"
    assert is_within(tmp_path, child)


def test_is_within_base_itself(tmp_path):
    assert is_within(tmp_path, tmp_path)


def test_is_within_outside(tmp_path):
    base = tmp_path / "base"
    other = tmp_path / "other" / "file.txt"
    base.mkdir()
    assert not is_within(base, other)


def test_is_within_parent(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    assert not is_within(base, tmp_path)


def test_is_within_lexical_dotdot_inside(tmp_path):
    assert is_within(tmp_path, tmp_path / "a" / ".." / "b")


def test_resolve_within_returns_path(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "note.txt").write_text("hi")
    result = resolve_within(tmp_path, "docs", "note.txt")
    assert result == (tmp_path / "docs" / "note.txt").resolve()


def test_resolve_within_rejects_traversal(tmp_path):
    with pytest.raises(PathTraversalError):
        resolve_within(tmp_path, "../escape.txt")


def test_resolve_within_rejects_absolute(tmp_path):
    with pytest.raises(PathTraversalError):
        resolve_within(tmp_path, "/etc/passwd")


@requires_symlinks
def test_resolve_within_symlink_escape(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("top secret")
    (base / "innocent.txt").symlink_to(secret)
    with pytest.raises(SymlinkEscapeError):
        resolve_within(base, "innocent.txt")


@requires_symlinks
def test_resolve_within_symlink_inside_ok(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    real = base / "real.txt"
    real.write_text("fine")
    (base / "alias.txt").symlink_to(real)
    assert resolve_within(base, "alias.txt") == real.resolve()
