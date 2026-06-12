from pathward import (
    FileChangedError,
    PathTraversalError,
    PathwardError,
    SymlinkEscapeError,
    UnsafeArchiveError,
)


def test_all_errors_subclass_pathward_error():
    for exc in (
        PathTraversalError,
        SymlinkEscapeError,
        UnsafeArchiveError,
        FileChangedError,
    ):
        assert issubclass(exc, PathwardError)


def test_traversal_error_is_value_error():
    assert issubclass(PathTraversalError, ValueError)
