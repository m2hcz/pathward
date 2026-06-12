from pathlib import Path

import pytest

from pathward import PathTraversalError, safe_join


def test_joins_single_part(tmp_path):
    assert safe_join(tmp_path, "file.txt") == tmp_path / "file.txt"


def test_joins_nested_parts(tmp_path):
    assert safe_join(tmp_path, "a", "b", "c.txt") == tmp_path / "a" / "b" / "c.txt"


def test_joins_multi_segment_string(tmp_path):
    assert safe_join(tmp_path, "a/b/c.txt") == tmp_path / "a" / "b" / "c.txt"


def test_allows_dot_segments(tmp_path):
    assert safe_join(tmp_path, "./a/./b") == tmp_path / "a" / "b"


def test_accepts_path_objects(tmp_path):
    assert safe_join(tmp_path, Path("a"), Path("b.txt")) == tmp_path / "a" / "b.txt"


def test_no_parts_returns_base(tmp_path):
    assert safe_join(tmp_path) == tmp_path


def test_rejects_parent_directory(tmp_path):
    with pytest.raises(PathTraversalError):
        safe_join(tmp_path, "..")


def test_rejects_embedded_traversal(tmp_path):
    with pytest.raises(PathTraversalError):
        safe_join(tmp_path, "a/../../secret.txt")


def test_rejects_backslash_traversal(tmp_path):
    with pytest.raises(PathTraversalError):
        safe_join(tmp_path, "..\\secret.txt")


def test_rejects_absolute_posix(tmp_path):
    with pytest.raises(PathTraversalError):
        safe_join(tmp_path, "/etc/passwd")


def test_rejects_windows_drive(tmp_path):
    with pytest.raises(PathTraversalError):
        safe_join(tmp_path, "C:\\Windows\\system32")
    with pytest.raises(PathTraversalError):
        safe_join(tmp_path, "C:relative")
    with pytest.raises(PathTraversalError):
        safe_join(tmp_path, "\\\\server\\share\\file")


def test_rejects_null_byte(tmp_path):
    with pytest.raises(PathTraversalError):
        safe_join(tmp_path, "file\x00.txt")
