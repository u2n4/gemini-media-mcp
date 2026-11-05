"""Security and retry regressions after the Omni rename; no live Gemini calls."""

import base64
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from omni_mcp_server import server as s
from omni_mcp_server.core.validation import ValidationError, validate_output_path, validate_video_uri


@pytest.mark.parametrize("path", [r"\\?\C:\Windows\video.mp4", r"\\.\C:\Windows\video.mp4",
                                  "//etc/video.mp4", r"C:\Windows\video.mp4"])
def test_disguised_system_paths(path):
    with pytest.raises(ValidationError, match="Device paths|blocked system"):
        validate_output_path(path)


@pytest.mark.parametrize("uri", [
    "https://generativelanguage.googleapis.com.attacker.example/video.mp4",
    "https://generativelanguage.googleapis.com:443/video.mp4",
    "https://generativelanguage.googleapis.com/\nvideo.mp4",
])
def test_host_only_prefix_cannot_expand_trust(uri):
    with pytest.raises(ValidationError):
        validate_video_uri(uri, ("https://generativelanguage.googleapis.com",))


def test_rotation_tries_all_remaining_keys(monkeypatch):
    manager = NS(clients=[Mock(), Mock(), Mock()], current_index=0)

    def rotate():
        manager.current_index += 1
        return manager.current_index < len(manager.clients)

    manager.rotate = rotate
    monkeypatch.setattr(s, "_get_manager", lambda: manager)
    call = Mock(side_effect=[RuntimeError("429"), RuntimeError("RESOURCE_EXHAUSTED"), "ok"])
    assert s._call_with_rotation(call) == "ok"
    assert call.call_count == 3
    call = Mock(side_effect=RuntimeError("permission denied"))
    with pytest.raises(RuntimeError, match="permission denied"):
        s._call_with_rotation(call)
    assert call.call_count == 1


def test_save_checks_actual_path_again(tmp_path):
    blocked = tmp_path / ".ssh" / "video.mp4"
    # Protect a replaced output target, not just the tool's original path.
    target = tmp_path / "video.mp4"
    try:
        target.symlink_to(blocked)
    except OSError:
        pytest.skip("OS does not permit creating symlinks")
    interaction = NS(output_video=NS(data=base64.b64encode(b"fake").decode(), uri=None))
    with pytest.raises(ValidationError, match="protected"):
        s._save_video(interaction, target, Mock())
