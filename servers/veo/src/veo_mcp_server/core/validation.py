"""Filesystem path and URI validation for veo-mcp-server.

Prevents:
- Arbitrary filesystem WRITE via ``output_path`` (e.g. overwriting
  ``~/.ssh/authorized_keys``, ``C:\\Windows\\System32\\...``).
- Arbitrary filesystem READ via ``image_path`` / ``first_frame_path`` /
  ``last_frame_path`` (e.g. exfiltrating ``~/.aws/credentials``).
- SSRF-like abuse via ``video_uri`` pointing at cloud metadata endpoints,
  ``file://`` local files, or plain-HTTP hosts.

Derived from ``nanobanana_mcp_server.core.validation`` but hardened for the
video-generation threat surface documented in
``references/threat-models/python-monorepo.md``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse


class ValidationError(ValueError):
    """Raised when a user-supplied input fails security validation."""


VIDEO_EXTENSIONS: Tuple[str, ...] = (".mp4", ".mov")
IMAGE_EXTENSIONS: Tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp")

ALLOWED_VIDEO_URI_PREFIXES: Tuple[str, ...] = (
    "https://generativelanguage.googleapis.com/",
    "https://aiplatform.googleapis.com/",
    "https://us-central1-aiplatform.googleapis.com/",
)

MAX_IMAGE_SIZE_BYTES: int = 50 * 1024 * 1024
MAX_PATH_LEN: int = 1024
MAX_URI_LEN: int = 2048


_BLOCKED_SYSTEM_DIRS: Tuple[str, ...] = (
    # Windows
    r"C:\Windows",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\ProgramData",
    r"C:\System Volume Information",
    r"C:\$Recycle.Bin",
    # POSIX
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/boot",
    "/root",
    "/var/log",
    "/var/spool",
    # macOS
    "/System",
    "/Library",
    "/Applications",
)

_BLOCKED_HOME_SUBDIRS: Tuple[str, ...] = (
    ".ssh",
    ".aws",
    ".gnupg",
    ".gcp",
    ".docker",
    ".kube",
    ".netrc",
    ".git-credentials",
    ".config/gh",
    ".config/claude",
    "AppData/Roaming/Microsoft",
    "AppData/Roaming/Google/Chrome",
    "AppData/Local/Microsoft",
    "AppData/Local/Google/Chrome",
    "AppData/Local/Packages",
)


def _norm(p: Path | str) -> str:
    """Normalize a path for string comparison (Windows-safe, case-insensitive)."""
    return str(p).replace("\\", "/").rstrip("/").lower()


def _is_inside(child: Path, parent: str) -> bool:
    """True if ``child`` resolves inside ``parent`` (string-level match)."""
    c = _norm(child)
    p = _norm(Path(parent))
    return c == p or c.startswith(p + "/")


def _check_not_in_blocked_dirs(resolved: Path, original: str = "") -> None:
    """Raise if ``resolved`` lands under any blocked system or user dir.

    Also checks the ORIGINAL user-supplied path against POSIX-style blocked
    roots. On Windows, ``Path("/etc/x").resolve()`` re-roots to ``C:\\etc\\x``
    so the resolved check alone misses obvious ``/etc/...`` attempts.
    """
    for blocked in _BLOCKED_SYSTEM_DIRS:
        if _is_inside(resolved, blocked):
            raise ValidationError(
                f"Path resolves into blocked system directory: {blocked}"
            )

    if original:
        norm_original = original.replace("\\", "/").rstrip("/").lower()
        for blocked in _BLOCKED_SYSTEM_DIRS:
            if not blocked.startswith("/"):
                continue  # only POSIX patterns benefit from this extra check
            b = blocked.lower()
            if norm_original == b or norm_original.startswith(b + "/"):
                raise ValidationError(
                    f"Path resolves into blocked system directory: {blocked}"
                )

    home = Path.home().resolve()
    for sub in _BLOCKED_HOME_SUBDIRS:
        candidate = home / sub
        if _is_inside(resolved, str(candidate)):
            raise ValidationError(
                f"Path resolves into protected user directory: ~/{sub}"
            )


def _resolve_strict(user_path: str) -> Path:
    """Strictly expand + resolve a user-supplied path.

    Rejects empty strings, NUL bytes, over-long paths, and literal ``..`` parts
    (we also run ``resolve()`` afterward, which collapses them — but an attacker
    using ``..`` is a signal we want surfaced in the error).
    """
    if not user_path or not user_path.strip():
        raise ValidationError("Path cannot be empty")
    if len(user_path) > MAX_PATH_LEN:
        raise ValidationError(f"Path too long (max {MAX_PATH_LEN} chars)")
    if "\x00" in user_path:
        raise ValidationError("Path contains NUL byte")

    expanded = os.path.expanduser(user_path)
    p = Path(expanded)

    for part in p.parts:
        if part == "..":
            raise ValidationError("Path traversal (`..`) not permitted")

    try:
        resolved = p.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ValidationError(f"Cannot resolve path: {exc}") from exc
    return resolved


def validate_output_path(
    path: str,
    allowed_extensions: Tuple[str, ...] = VIDEO_EXTENSIONS,
) -> Path:
    """Validate a user-supplied output path.

    - Blocks writes to system dirs (``C:\\Windows``, ``/etc``, ...).
    - Blocks writes to sensitive user dirs (``~/.ssh``, ``~/.aws``, ...).
    - Enforces extension from ``allowed_extensions``.
    - Rejects path traversal and NUL bytes.

    Returns the resolved (not-necessarily-existing) Path so callers can ``mkdir``.
    """
    resolved = _resolve_strict(path)
    _check_not_in_blocked_dirs(resolved, original=path)

    ext = resolved.suffix.lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f"Output extension {ext!r} not allowed. Permitted: {allowed_extensions}"
        )
    return resolved


def validate_file_path(
    path: str,
    allowed_extensions: Tuple[str, ...] = IMAGE_EXTENSIONS,
    max_size_bytes: int = MAX_IMAGE_SIZE_BYTES,
) -> Path:
    """Validate a user-supplied input file path.

    - Must exist and be a regular file.
    - Must land outside blocked system / user dirs (symlink-safe: checks
      the ``resolve()``-d path).
    - Must have an allowed extension.
    - Must be <= ``max_size_bytes``.

    Returns the resolved Path.
    """
    resolved = _resolve_strict(path)
    _check_not_in_blocked_dirs(resolved, original=path)

    if not resolved.exists():
        raise ValidationError(f"File not found: {path}")
    if not resolved.is_file():
        raise ValidationError(f"Path is not a regular file: {path}")

    try:
        size = resolved.stat().st_size
    except OSError as exc:
        raise ValidationError(f"Cannot stat file: {exc}") from exc
    if size > max_size_bytes:
        raise ValidationError(
            f"File too large ({size} bytes, max {max_size_bytes})"
        )

    ext = resolved.suffix.lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f"Input extension {ext!r} not allowed. Permitted: {allowed_extensions}"
        )
    return resolved


def validate_video_uri(
    uri: str,
    allowed_prefixes: Tuple[str, ...] = ALLOWED_VIDEO_URI_PREFIXES,
) -> str:
    """Validate a VEO-extensible video URI.

    - Must start with an allowed prefix (Gemini / Vertex AI Files API).
    - Rejects ``file://``, ``ftp://``, ``gopher://``, ``http://`` (non-TLS),
      ``javascript:``, ``data:``.
    - Rejects URIs with credentials embedded (``user:pass@host``).

    Returns the URI unchanged for caller use.
    """
    if not uri or not uri.strip():
        raise ValidationError("Video URI cannot be empty")
    if len(uri) > MAX_URI_LEN:
        raise ValidationError(f"Video URI too long (max {MAX_URI_LEN} chars)")

    try:
        parsed = urlparse(uri)
    except Exception as exc:
        raise ValidationError(f"Invalid URI: {exc}") from exc

    if parsed.scheme != "https":
        raise ValidationError(
            f"Video URI must use https scheme (got {parsed.scheme!r})"
        )
    if parsed.username or parsed.password:
        raise ValidationError("Video URI must not include credentials")

    if not any(uri.startswith(p) for p in allowed_prefixes):
        raise ValidationError(
            "Video URI does not match any allowed prefix. "
            f"Allowed: {allowed_prefixes}"
        )
    return uri
