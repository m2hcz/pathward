# pathward

Defensive Python library against **path traversal**, **symlink escape**, **Zip Slip**, and **TOCTOU** races.

Inspired by the File Browser symlink disclosure, where symlinks planted inside a served directory allowed reading arbitrary files on the host. `pathward` makes the safe thing the easy thing: every API takes a *base* directory and refuses to touch anything outside it.

- Zero dependencies, pure standard library
- Python 3.9 – 3.13, Linux / macOS / Windows
- 54 tests, CI across all supported versions and platforms

## Install

```bash
pip install pathward
```

Or from source:

```bash
pip install -e ".[dev]"
pytest
```

## Quick start

```python
from pathward import safe_join, resolve_within, safe_open, safe_extract

base = "/srv/app/uploads"

# Lexical join that cannot escape base — rejects "..", absolute paths,
# drive letters, UNC prefixes and null bytes:
path = safe_join(base, user_supplied_name)        # PathTraversalError on attack

# Join + resolve + containment check (catches symlink escapes too):
real = resolve_within(base, "docs", filename)     # SymlinkEscapeError on escape

# Open a file with symlink refusal, O_NOFOLLOW and post-open fd verification:
with safe_open(base, filename) as f:              # TOCTOU-hardened
    data = f.read()

# Extract zip/tar archives without Zip Slip, link members, or bombs:
safe_extract("upload.zip", base, max_members=1000, max_total_size=100_000_000)
```

## API

### Path containment — `pathward.resolve`

| Function | Description |
| --- | --- |
| `safe_join(base, *parts)` | Lexically join parts onto base. Raises `PathTraversalError` for `..`, absolute paths, drives, UNC, null bytes. Treats `/` and `\` as separators on every platform. |
| `is_within(base, target)` | `True` if `target` *resolves* inside `base` (symlinks followed). |
| `resolve_within(base, *parts)` | `safe_join` + full resolution + containment check. Raises `SymlinkEscapeError` if a symlink redirects the path outside `base`. |

### Symlink defense — `pathward.links`

| Function | Description |
| --- | --- |
| `find_symlink(base, path)` | Returns the first symlink component between `base` and `path`, or `None`. |
| `contains_symlink(base, path)` | Boolean form of the above. |
| `assert_no_symlinks(base, path)` | Raises `SymlinkEscapeError` if any component is a symlink. |
| `safe_open(base, *parts, mode="r", follow_symlinks=False)` | Containment-checked `open()`. By default refuses every symlink, opens with `O_NOFOLLOW` where available, and cross-checks the opened descriptor against the path (`fstat` vs `lstat`) to detect swaps in the race window. With `follow_symlinks=True`, symlinks are allowed only if the resolved target stays inside `base`. |

### Safe extraction — `pathward.archive`

| Function | Description |
| --- | --- |
| `safe_extract_zip(src, dest, *, max_members=None, max_total_size=None)` | Extract a zip, rejecting Zip Slip member names and symlink members. |
| `safe_extract_tar(src, dest, *, max_members=None, max_total_size=None)` | Extract a tar, additionally rejecting hardlinks and device nodes. Metadata (modes, owners) is deliberately not preserved. |
| `safe_extract(src, dest, ...)` | Auto-detects zip vs tar. |

All extraction functions validate **before** writing anything for size/count limits, validate each member name lexically, and return the list of extracted file paths.

### Errors — `pathward.errors`

```text
PathwardError
├── PathTraversalError (also a ValueError)   — lexical escape attempt
├── SymlinkEscapeError                       — symlink leads outside base
├── UnsafeArchiveError                       — Zip Slip / link member / bomb
└── FileChangedError                         — file swapped mid-operation (TOCTOU)
```

Catch `PathwardError` at trust boundaries to handle all of them uniformly.

## Threat model and guarantees

| Threat | Defense |
| --- | --- |
| `../../etc/passwd` in user input | `safe_join` rejects lexically, before any filesystem access. |
| Absolute / drive / UNC paths (`/etc/x`, `C:\x`, `\\srv\share`) | Rejected on every platform, regardless of where the code runs. |
| Separator smuggling (`..\` on Linux) | Both `/` and `\` are always treated as separators. |
| Null-byte truncation | Rejected. |
| Symlink planted inside the tree pointing outside (File Browser-style) | `resolve_within` / `safe_open` detect post-resolution escape; `safe_open` refuses symlinks entirely by default. |
| Zip Slip (`../` in archive member names) | Every member name is validated with `safe_join` before extraction. |
| Symlink / hardlink / device archive members | Rejected. |
| Decompression bombs | Opt-in `max_members` / `max_total_size` limits, checked up front. |
| TOCTOU file swap at open time | `O_NOFOLLOW` on POSIX plus post-open `fstat`/`lstat` identity check. |

**Honest limitations:** on Windows there is no `O_NOFOLLOW`, so `safe_open` relies on the pre-check plus the post-open descriptor identity check (best effort). Intermediate-directory races on POSIX are narrowed but not fully eliminated without `openat2`-style APIs. Treat `pathward` as a strong layer of defense, not a substitute for OS-level sandboxing.

## Development

```bash
pip install -e ".[dev]"
pytest -v
```

CI runs the full suite on Ubuntu, Windows and macOS across Python 3.9, 3.10, 3.11, 3.12 and 3.13.

## License

MIT
