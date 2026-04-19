"""Security tests for veo_mcp_server.core.validation + tool-level wiring.

Covers threat-model items 3.1 (arbitrary file write/read via output_path /
image_path) and 3.3 (SSRF via video_uri).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from veo_mcp_server.core.validation import (
    ValidationError,
    validate_file_path,
    validate_output_path,
    validate_video_uri,
)


# ---------- validate_output_path ----------


def test_output_path_rejects_empty():
    with pytest.raises(ValidationError):
        validate_output_path("")


def test_output_path_blocks_windows_system_dirs():
    with pytest.raises(ValidationError, match="blocked system"):
        validate_output_path(r"C:\Windows\System32\evil.mp4")


def test_output_path_blocks_program_files():
    with pytest.raises(ValidationError, match="blocked system"):
        validate_output_path(r"C:\Program Files\evil.mp4")


def test_output_path_blocks_unix_etc():
    with pytest.raises(ValidationError, match="blocked system"):
        validate_output_path("/etc/evil.mp4")


def test_output_path_blocks_unix_usr_bin():
    with pytest.raises(ValidationError, match="blocked system"):
        validate_output_path("/usr/bin/evil.mp4")


def test_output_path_blocks_ssh_keys():
    with pytest.raises(ValidationError, match="protected user directory"):
        validate_output_path("~/.ssh/id_rsa.mp4")


def test_output_path_blocks_aws_credentials():
    with pytest.raises(ValidationError, match="protected user directory"):
        validate_output_path("~/.aws/credentials.mp4")


def test_output_path_blocks_traversal():
    with pytest.raises(ValidationError, match="traversal"):
        validate_output_path("../../etc/passwd.mp4")


def test_output_path_blocks_nul_byte():
    with pytest.raises(ValidationError, match="NUL"):
        validate_output_path("good\x00.mp4")


def test_output_path_rejects_over_long():
    with pytest.raises(ValidationError, match="too long"):
        validate_output_path("a" * 2000 + ".mp4")


def test_output_path_enforces_extension(tmp_path):
    bad = tmp_path / "vid.exe"
    with pytest.raises(ValidationError, match="extension"):
        validate_output_path(str(bad))


def test_output_path_accepts_mp4(tmp_path):
    p = tmp_path / "out.mp4"
    resolved = validate_output_path(str(p))
    assert resolved.suffix == ".mp4"


def test_output_path_accepts_mov(tmp_path):
    p = tmp_path / "out.mov"
    resolved = validate_output_path(str(p))
    assert resolved.suffix == ".mov"


# ---------- validate_file_path ----------


def test_file_path_rejects_empty():
    with pytest.raises(ValidationError):
        validate_file_path("")


def test_file_path_requires_exists():
    with pytest.raises(ValidationError, match="File not found"):
        validate_file_path("/definitely/does/not/exist.png")


def test_file_path_blocks_ssh_keys():
    # Use an invented but existent-looking path — resolution alone should block
    # before existence check.
    with pytest.raises(ValidationError, match="protected user directory"):
        validate_file_path("~/.ssh/id_rsa.png")


def test_file_path_blocks_windows_system():
    with pytest.raises(ValidationError, match="blocked system"):
        validate_file_path(r"C:\Windows\System32\notepad.exe")


def test_file_path_rejects_non_image_ext(tmp_path):
    p = tmp_path / "fake.txt"
    p.write_text("not an image")
    with pytest.raises(ValidationError, match="extension"):
        validate_file_path(str(p))


def test_file_path_accepts_png(tmp_path):
    p = tmp_path / "img.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n")
    resolved = validate_file_path(str(p))
    assert resolved.exists()
    assert resolved.suffix == ".png"


def test_file_path_rejects_too_large(tmp_path):
    p = tmp_path / "huge.png"
    p.write_bytes(b"\x89PNG" + b"A" * 2048)
    with pytest.raises(ValidationError, match="too large"):
        validate_file_path(str(p), max_size_bytes=1024)


def test_file_path_rejects_traversal():
    with pytest.raises(ValidationError, match="traversal"):
        validate_file_path("../../etc/passwd.png")


# ---------- validate_video_uri ----------


def test_video_uri_accepts_gemini_files_api():
    uri = "https://generativelanguage.googleapis.com/v1beta/files/abc123"
    assert validate_video_uri(uri) == uri


def test_video_uri_accepts_vertex_ai():
    uri = (
        "https://aiplatform.googleapis.com/v1/projects/x/locations/"
        "us-central1/files/y"
    )
    assert validate_video_uri(uri) == uri


def test_video_uri_rejects_file_scheme():
    with pytest.raises(ValidationError, match="https scheme"):
        validate_video_uri("file:///etc/passwd")


def test_video_uri_rejects_http():
    with pytest.raises(ValidationError, match="https scheme"):
        validate_video_uri(
            "http://generativelanguage.googleapis.com/v1beta/files/x"
        )


def test_video_uri_rejects_metadata_endpoint():
    with pytest.raises(ValidationError, match="allowed prefix"):
        validate_video_uri("https://169.254.169.254/metadata")


def test_video_uri_rejects_embedded_credentials():
    with pytest.raises(ValidationError, match="credentials"):
        validate_video_uri(
            "https://user:pass@generativelanguage.googleapis.com/v1beta/files/x"
        )


def test_video_uri_rejects_empty():
    with pytest.raises(ValidationError):
        validate_video_uri("")


def test_video_uri_rejects_ftp():
    with pytest.raises(ValidationError, match="https scheme"):
        validate_video_uri("ftp://generativelanguage.googleapis.com/file")


def test_video_uri_rejects_over_long():
    long_uri = "https://generativelanguage.googleapis.com/" + "a" * 3000
    with pytest.raises(ValidationError, match="too long"):
        validate_video_uri(long_uri)


# ---------- tool-level wiring (one test per tool) ----------


def test_veo_generate_video_rejects_bad_output_path():
    """veo_generate_video must reject a malicious output_path before starting a thread."""
    from veo_mcp_server.server import veo_generate_video

    with pytest.raises(ValidationError):
        veo_generate_video(
            prompt="test",
            output_path=str(Path.home() / ".ssh" / "evil.mp4"),
        )


def test_veo_image_to_video_rejects_bad_image_path():
    """veo_image_to_video must reject an image_path that targets system files."""
    from veo_mcp_server.server import veo_image_to_video

    with pytest.raises(ValidationError):
        veo_image_to_video(
            prompt="animate",
            image_path=r"C:\Windows\System32\notepad.exe",
        )


def test_veo_extend_video_rejects_bad_video_uri():
    """veo_extend_video must reject non-Gemini URIs."""
    from veo_mcp_server.server import veo_extend_video

    with pytest.raises(ValidationError):
        veo_extend_video(
            prompt="continue",
            video_uri="file:///etc/passwd",
        )


def test_veo_interpolate_video_rejects_bad_frame_path():
    """veo_interpolate_video must reject frame paths targeting user dotfiles."""
    from veo_mcp_server.server import veo_interpolate_video

    with pytest.raises(ValidationError):
        veo_interpolate_video(
            prompt="blend",
            first_frame_path="~/.ssh/id_rsa.png",
            last_frame_path="~/.ssh/id_rsa.png",
        )
