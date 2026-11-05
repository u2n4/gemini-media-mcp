"""Omni request, download and MCP contracts; all Gemini calls are fakes."""
import asyncio
import base64
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from veo_mcp_server import server as s


@pytest.fixture
def fake_client(monkeypatch):
    client = Mock()
    client.interactions.create.return_value = NS(
        output_video=NS(data=base64.b64encode(b"fake-video").decode(), uri=None)
    )
    monkeypatch.setattr(s, "_manager", NS(client=client))
    monkeypatch.setattr(s, "jobs", {})

    # Exercise the real worker deterministically, without leaving running threads.
    def thread(*, target, args, daemon):
        return NS(start=lambda: target(*args))

    monkeypatch.setattr(s.threading, "Thread", thread)
    monkeypatch.setattr(s.time, "sleep", lambda _: None)
    return client


def test_text_request_and_completed_job(fake_client, tmp_path):
    target = tmp_path / "text.mp4"
    message = s.veo_generate_video("A sunset", resolution="4k", duration_seconds=15,
                                   aspect_ratio="9:16", output_path=str(target))
    fake_client.interactions.create.assert_called_once_with(
        model="gemini-omni-1.2-flash", input="A sunset",
        response_format={"type": "video", "duration": "15s", "aspect_ratio": "9:16",
                         "resolution": "4k", "delivery": "uri"},
    )
    jid, job = next(iter(s.jobs.items()))
    assert jid in message
    assert job["status"] == "completed"
    assert job["result_paths"] == [str(target)]
    assert target.read_bytes() == b"fake-video"
    assert "Video is ready!" in s.veo_check_job(jid)
    assert "veo_extend_video" not in s.veo_check_job(jid)


@pytest.mark.parametrize("suffix,mime", [(".jpg", "image/jpeg"), (".png", "image/png"),
                                        (".webp", "image/webp")])
def test_image_input_and_default_duration(fake_client, tmp_path, suffix, mime):
    image = tmp_path / ("source" + suffix)
    image.write_bytes(b"fake-image")
    s.veo_image_to_video("Animate", str(image), output_path=str(tmp_path / "image.mp4"))
    request = fake_client.interactions.create.call_args.kwargs
    assert request["input"] == [
        {"type": "image", "data": base64.b64encode(b"fake-image").decode(), "mime_type": mime},
        {"type": "text", "text": "Animate"},
    ]
    assert request["response_format"]["duration"] == "10s"
    assert next(iter(s.jobs.values()))["status"] == "completed"


def test_uri_poll_then_download(fake_client, tmp_path):
    uri = "https://generativelanguage.googleapis.com/v1beta/files/video-id"
    fake_client.interactions.create.return_value = NS(output_video=NS(data=None, uri=uri))
    fake_client.files.get.side_effect = [NS(state=NS(name="PROCESSING")), NS(state=NS(name="ACTIVE"))]
    fake_client.files.download.side_effect = lambda **kw: Path(kw["destination"]).write_bytes(b"downloaded")
    target = tmp_path / "uri.mp4"
    s.veo_generate_video("A sunset", output_path=str(target))
    assert fake_client.files.get.call_count == 2
    fake_client.files.get.assert_called_with(name="files/video-id")
    fake_client.files.download.assert_called_once_with(file=uri, destination=str(target))
    assert target.read_bytes() == b"downloaded"
    assert next(iter(s.jobs.values()))["status"] == "completed"


def test_processing_failure_marks_job_failed(fake_client, tmp_path):
    fake_client.interactions.create.return_value = NS(output_video=NS(
        data=None, uri="https://generativelanguage.googleapis.com/v1beta/files/failed"))
    fake_client.files.get.return_value = NS(state=NS(name="FAILED"))
    s.veo_generate_video("fail", output_path=str(tmp_path / "failed.mp4"))
    job = next(iter(s.jobs.values()))
    assert job["status"] == "failed"
    assert "FAILED" in job["error"]
    fake_client.files.download.assert_not_called()


def test_file_poll_timeout(fake_client, monkeypatch, tmp_path):
    monkeypatch.setattr(s, "FILE_POLL_TIMEOUT", 0)
    fake_client.files.get.return_value = NS(state=NS(name="PROCESSING"))
    video = NS(output_video=NS(data=None, uri="https://generativelanguage.googleapis.com/v1beta/files/slow"))
    with pytest.raises(TimeoutError, match="ACTIVE"):
        s._save_video(video, tmp_path / "slow.mp4", fake_client)
    fake_client.files.download.assert_not_called()


@pytest.mark.parametrize("video", [None, NS(data=None, uri=None), NS(data="", uri=None),
                                   NS(data="not base64!", uri=None)])
def test_bad_output_is_an_error(fake_client, tmp_path, video):
    fake_client.interactions.create.return_value = NS(output_video=video)
    s.veo_generate_video("bad output", output_path=str(tmp_path / "bad.mp4"))
    assert next(iter(s.jobs.values()))["status"] == "failed"


def test_download_error_is_reported(fake_client, tmp_path):
    fake_client.interactions.create.side_effect = RuntimeError("fake API failure")
    s.veo_generate_video("fail", output_path=str(tmp_path / "failed.mp4"))
    assert next(iter(s.jobs.values()))["error"] == "fake API failure"


@pytest.mark.parametrize("duration", [2, 16, 3.5, True])
def test_invalid_duration(fake_client, duration):
    with pytest.raises(ValueError, match="duration_seconds"):
        s.veo_generate_video("test", duration_seconds=duration)
    fake_client.interactions.create.assert_not_called()


@pytest.mark.parametrize("tool", ["text", "image", "status"])
def test_missing_key(monkeypatch, tmp_path, tool):
    monkeypatch.setattr(s, "_manager", None)
    monkeypatch.setattr(s, "API_KEYS", [])
    image = tmp_path / "image.jpg"
    image.write_bytes(b"fake")
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        if tool == "text":
            s.veo_generate_video("test")
        elif tool == "image":
            s.veo_image_to_video("test", str(image))
        else:
            s.veo_api_status()


def test_mcp_tool_list():
    tools = asyncio.run(s.mcp.list_tools())
    assert {tool.name for tool in tools} == {
        "veo_generate_video", "veo_image_to_video", "veo_check_job", "veo_list_jobs",
        "veo_show_output_stats", "veo_pricing_info", "veo_api_status",
    }
    schema = next(t for t in tools if t.name == "veo_generate_video").inputSchema
    assert "seed" not in schema["properties"]
    assert schema["properties"]["duration_seconds"]["default"] == 10
    assert s._get_model("fast") == s._get_model("standard") == "gemini-omni-1.2-flash"
