"""Resolve local paths before reading or writing, including symlink targets."""

import re
from pathlib import Path

from ..core.exceptions import ValidationError


_SYSTEM_DIRS = (
    "/etc", "/usr", "/bin", "/sbin", "/boot", "/root", "/proc", "/sys",
    "/dev", "/var/log", "/var/spool", "/System", "/Library", "/Applications",
)
_SENSITIVE_PARTS = {
    ".ssh", ".aws", ".gnupg", ".gcp", ".docker", ".kube", ".netrc",
    ".git-credentials", ".env", ".codex", ".claude", ".grok",
}
_SENSITIVE_DIRS = (
    ".config/gh", ".config/gcloud", ".config/claude",
    "appdata/roaming/microsoft", "appdata/local/microsoft",
    "appdata/roaming/google", "appdata/local/google", "appdata/local/packages",
)


def resolve_safe_path(path: str) -> Path:
    """Allow absolute and relative local paths, reject traversal and secrets."""
    if not isinstance(path, str) or not path.strip():
        raise ValidationError("Path cannot be empty")
    if len(path) > 4096 or any(ord(c) < 32 for c in path):
        raise ValidationError("Path contains control characters or is too long")
    raw = path.replace("\\", "/")
    if raw.startswith(("//?/", "//./")):
        raise ValidationError("Device paths are not permitted")
    if ".." in raw.split("/"):
        raise ValidationError("Path traversal (`..`) not permitted")
    try:
        resolved = Path(path).expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValidationError("Cannot resolve path") from exc
    for candidate in (raw, resolved.as_posix()):
        normal = "/" + candidate.lstrip("/").casefold() if candidate.startswith("/") else candidate.casefold()
        if any(normal == b.casefold() or normal.startswith(b.casefold() + "/") for b in _SYSTEM_DIRS):
            raise ValidationError("Path resolves into a blocked system directory")
        # Check Windows drive roots even when validation runs on another OS.
        if re.match(r"^[a-z]:/(windows|program files(?: \(x86\))?|programdata|system volume information|\$recycle\.bin)(/|$)", normal):
            raise ValidationError("Path resolves into a blocked system directory")
        parts = normal.split("/")
        if any(part in _SENSITIVE_PARTS for part in parts) or any(
            f"/{sub}/" in f"/{normal.strip('/')}/" for sub in _SENSITIVE_DIRS
        ):
            raise ValidationError("Path resolves into a protected user directory")
    return resolved
