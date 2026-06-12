import stat
import zipfile

import pytest

from pathward import UnsafeArchiveError, safe_extract_zip


def make_zip(path, entries):
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries:
            zf.writestr(name, data)
    return path


def test_extracts_files(tmp_path):
    archive = make_zip(tmp_path / "a.zip", [("hello.txt", "world")])
    dest = tmp_path / "out"
    safe_extract_zip(archive, dest)
    assert (dest / "hello.txt").read_text() == "world"


def test_preserves_directory_structure(tmp_path):
    archive = make_zip(
        tmp_path / "a.zip",
        [("docs/readme.md", "# hi"), ("docs/sub/deep.txt", "deep")],
    )
    dest = tmp_path / "out"
    safe_extract_zip(archive, dest)
    assert (dest / "docs" / "readme.md").read_text() == "# hi"
    assert (dest / "docs" / "sub" / "deep.txt").read_text() == "deep"


def test_rejects_dotdot_member(tmp_path):
    archive = make_zip(tmp_path / "evil.zip", [("../escape.txt", "pwned")])
    with pytest.raises(UnsafeArchiveError):
        safe_extract_zip(archive, tmp_path / "out")
    assert not (tmp_path / "escape.txt").exists()


def test_rejects_absolute_member(tmp_path):
    archive = make_zip(tmp_path / "evil.zip", [("/etc/cron.d/evil", "pwned")])
    with pytest.raises(UnsafeArchiveError):
        safe_extract_zip(archive, tmp_path / "out")


def test_rejects_symlink_member(tmp_path):
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        info = zipfile.ZipInfo("link.txt")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(info, "/etc/passwd")
    with pytest.raises(UnsafeArchiveError):
        safe_extract_zip(archive, tmp_path / "out")


def test_max_members_limit(tmp_path):
    archive = make_zip(
        tmp_path / "many.zip", [(f"f{i}.txt", "x") for i in range(5)]
    )
    with pytest.raises(UnsafeArchiveError):
        safe_extract_zip(archive, tmp_path / "out", max_members=3)


def test_max_total_size_limit(tmp_path):
    archive = make_zip(tmp_path / "big.zip", [("big.txt", "A" * 1000)])
    with pytest.raises(UnsafeArchiveError):
        safe_extract_zip(archive, tmp_path / "out", max_total_size=100)


def test_returns_extracted_paths(tmp_path):
    archive = make_zip(tmp_path / "a.zip", [("one.txt", "1"), ("two.txt", "2")])
    dest = tmp_path / "out"
    paths = safe_extract_zip(archive, dest)
    assert sorted(p.name for p in paths) == ["one.txt", "two.txt"]


def test_error_carries_member_name(tmp_path):
    archive = make_zip(tmp_path / "evil.zip", [("../escape.txt", "pwned")])
    with pytest.raises(UnsafeArchiveError) as excinfo:
        safe_extract_zip(archive, tmp_path / "out")
    assert excinfo.value.member == "../escape.txt"
