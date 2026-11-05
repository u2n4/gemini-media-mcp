"""Omni request, download and MCP contracts; all Gemini calls are fakes."""
import asyncio
import base64
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest
from google.genai.interactions import CreateModelInteraction

from omni_mcp_server import server as s


@pytest.fixture
def fake_client(monkeypatch):
    client = Mock()
    client.interactions.create.return_value = NS(
        output_video=NS(data=base64.b64encode(b"fake-video").decode(), uri=None)
    )

    def create(**request):
        # Validate the actual request against the installed SDK without a client.
        parsed = CreateModelInteraction.model_validate(request)
        assert set(request) <= set(parsed.model_dump(exclude_none=True))
        return client.interactions.create.return_value

    client.interactions.create.side_effect = create
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
    message = s.omni_generate_video("A sunset", resolution="4k", duration_seconds=15,
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
    assert "Video is ready!" in s.omni_check_job(jid)
    assert "omni_extend_video" not in s.omni_check_job(jid)


@pytest.mark.parametrize("suffix,mime", [(".jpg", "image/jpeg"), (".png", "image/png"),
                                        (".webp", "image/webp")])
def test_image_input_and_default_duration(fake_client, tmp_path, suffix, mime):
    image = tmp_path / ("source" + suffix)
    image.write_bytes(b"fake-image")
    s.omni_image_to_video("Animate", str(image), output_path=str(tmp_path / "image.mp4"))
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
    s.omni_generate_video("A sunset", output_path=str(target))
    assert fake_client.files.get.call_count == 2
    fake_client.files.get.assert_called_with(name="files/video-id")
    fake_client.files.download.assert_called_once_with(file=uri, destination=str(target))
    assert target.read_bytes() == b"downloaded"
    assert next(iter(s.jobs.values()))["status"] == "completed"


def test_processing_failure_marks_job_failed(fake_client, tmp_path):
    fake_client.interactions.create.return_value = NS(output_video=NS(
        data=None, uri="https://generativelanguage.googleapis.com/v1beta/files/failed"))
    fake_client.files.get.return_value = NS(state=NS(name="FAILED"))
    s.omni_generate_video("fail", output_path=str(tmp_path / "failed.mp4"))
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
    s.omni_generate_video("bad output", output_path=str(tmp_path / "bad.mp4"))
    assert next(iter(s.jobs.values()))["status"] == "failed"


def test_download_error_is_reported(fake_client, tmp_path):
    fake_client.interactions.create.side_effect = RuntimeError("fake API failure")
    s.omni_generate_video("fail", output_path=str(tmp_path / "failed.mp4"))
    assert next(iter(s.jobs.values()))["error"] == "fake API failure"


@pytest.mark.parametrize("duration", [2, 16, 3.5, True])
def test_invalid_duration(fake_client, duration):
    with pytest.raises(ValueError, match="duration_seconds"):
        s.omni_generate_video("test", duration_seconds=duration)
    fake_client.interactions.create.assert_not_called()


@pytest.mark.parametrize("tool", ["text", "image", "extend", "interpolate", "status"])
def test_missing_key(monkeypatch, tmp_path, tool):
    monkeypatch.setattr(s, "_manager", None)
    monkeypatch.setattr(s, "API_KEYS", [])
    image = tmp_path / "image.jpg"
    image.write_bytes(b"fake")
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        if tool == "text":
            s.omni_generate_video("test")
        elif tool == "image":
            s.omni_image_to_video("test", str(image))
        elif tool == "extend":
            s.omni_extend_video("test", video_uri="https://generativelanguage.googleapis.com/v1beta/files/source")
        elif tool == "interpolate":
            s.omni_interpolate_video("test", str(image), str(image))
        else:
            s.omni_api_status()


def test_mcp_tool_list():
    tools = asyncio.run(s.mcp.list_tools())
    assert {tool.name for tool in tools} == {
        "omni_generate_video", "omni_image_to_video", "omni_check_job", "omni_list_jobs",
        "omni_show_output_stats", "omni_pricing_info", "omni_api_status",
        "omni_extend_video", "omni_interpolate_video",
    }
    schema = next(t for t in tools if t.name == "omni_generate_video").input_schema
    assert "seed" not in schema["properties"]
    assert schema["properties"]["duration_seconds"]["default"] == 10
    assert s._get_model("fast") == s._get_model("standard") == "gemini-omni-1.2-flash"


@pytest.mark.parametrize("duration", [3, 10])
def test_extension_uri_request(fake_client, tmp_path, duration):
    uri = "https://generativelanguage.googleapis.com/v1beta/files/source"
    target = tmp_path / "extended.mp4"
    message = s.omni_extend_video("Continue the scene", video_uri=uri,
                                 duration_seconds=duration, output_path=str(target))
    fake_client.interactions.create.assert_called_once_with(
        model="gemini-omni-1.2-flash",
        input=[{"type": "video", "uri": uri},
               {"type": "text", "text": "Continue the scene"}],
        generation_config={"video_config": {"task": "extend"}},
        response_format={"type": "video", "duration": f"{duration}s", "resolution": "720p",
                         "delivery": "uri"},
    )
    jid, job = next(iter(s.jobs.items()))
    assert jid in message
    assert job["type"] == "extend-video"
    assert job["status"] == "completed"
    assert target.read_bytes() == b"fake-video"


def test_extension_from_source_job(fake_client, tmp_path):
    fake_client.interactions.create.return_value.id = "interaction-source"
    s.omni_generate_video("Start", output_path=str(tmp_path / "source.mp4"))
    source_id = next(iter(s.jobs))
    assert s.jobs[source_id]["interaction_id"] == "interaction-source"
    fake_client.interactions.create.reset_mock()
    s.omni_extend_video("Continue", source_job_id=source_id,
                       output_path=str(tmp_path / "extended.mp4"))
    request = fake_client.interactions.create.call_args.kwargs
    assert request["previous_interaction_id"] == "interaction-source"
    assert request["input"] == [{"type": "text", "text": "Continue"}]
    assert request["generation_config"] == {"video_config": {"task": "extend"}}
    assert request["response_format"]["duration"] == "10s"
    fake_client.files.upload.assert_not_called()


@pytest.mark.parametrize("duration", [3, 10])
def test_interpolation_request(fake_client, tmp_path, duration):
    first, last = tmp_path / "first.png", tmp_path / "last.jpg"
    first.write_bytes(b"first")
    last.write_bytes(b"last")
    target = tmp_path / "transition.mp4"
    message = s.omni_interpolate_video("Transition", str(first), str(last),
                                     duration_seconds=duration, output_path=str(target))
    fake_client.interactions.create.assert_called_once_with(
        model="gemini-omni-1.2-flash",
        input=[{"type": "image", "data": base64.b64encode(b"first").decode(),
                "mime_type": "image/png"},
               {"type": "image", "data": base64.b64encode(b"last").decode(),
                "mime_type": "image/jpeg"},
               {"type": "text", "text": "Transition"}],
        generation_config={"video_config": {"task": "image_to_video"}},
        response_format={"type": "video", "duration": f"{duration}s", "resolution": "1080p",
                         "delivery": "uri"},
    )
    jid, job = next(iter(s.jobs.items()))
    assert jid in message
    assert job["type"] == "interpolate"
    assert job["status"] == "completed"
    assert target.read_bytes() == b"fake-video"


@pytest.mark.parametrize("tool", ["omni_extend_video", "omni_interpolate_video"])
@pytest.mark.parametrize("duration", [2, 11, 15, 3.5, True])
def test_restored_tool_duration_limit(fake_client, tool, duration):
    args = {"video_uri": "https://generativelanguage.googleapis.com/v1beta/files/source"}
    if tool == "omni_interpolate_video":
        args = {"first_frame_path": "unused.png", "last_frame_path": "unused.png"}
    with pytest.raises(ValueError, match="duration_seconds must be an integer from 3 to 10"):
        getattr(s, tool)("test", duration_seconds=duration, **args)
    fake_client.interactions.create.assert_not_called()
    assert not s.jobs


def test_reference_images_request(fake_client, tmp_path):
    paths = [tmp_path / f"ref{i}.png" for i in range(6)]
    for path in paths:
        path.write_bytes(path.name.encode())
    s.omni_generate_video("Use these subjects", reference_image_paths=",".join(map(str, paths)),
                         duration_seconds=15, output_path=str(tmp_path / "refs.mp4"))
    request = fake_client.interactions.create.call_args.kwargs
    assert request["input"] == [s._load_image(str(path)) for path in paths] + [
        {"type": "text", "text": "Use these subjects"}]
    assert request["generation_config"] == {"video_config": {"task": "reference_to_video"}}


def test_too_many_reference_images(fake_client):
    with pytest.raises(ValueError, match="1 to 6"):
        s.omni_generate_video("test", reference_image_paths=",".join(["unused.png"] * 7))
    fake_client.interactions.create.assert_not_called()


@pytest.mark.parametrize("source_kind", ["uri", "local"])
def test_extension_older_source_job(fake_client, tmp_path, source_kind):
    uri = "https://generativelanguage.googleapis.com/v1beta/files/source"
    source = {"status": "completed"}
    local = tmp_path / "source.mp4"
    if source_kind == "uri":
        source["video_uri"] = uri
    else:
        local.write_bytes(b"old-video")
        source["result_path"] = str(local)
        fake_client.files.upload.return_value = NS(uri=uri)
    s.jobs["source"] = source
    s.omni_extend_video("Continue", source_job_id="source",
                       output_path=str(tmp_path / "extended.mp4"))
    request = fake_client.interactions.create.call_args.kwargs
    assert request["input"][0] == {"type": "video", "uri": uri}
    assert "previous_interaction_id" not in request
    assert len(s.jobs) == 2
    if source_kind == "local":
        fake_client.files.upload.assert_called_once_with(file=str(local))
    else:
        fake_client.files.upload.assert_not_called()


@pytest.mark.parametrize("source", [None, {"status": "generating"}, {"status": "completed"}])
def test_extension_unavailable_source(fake_client, source):
    if source is not None:
        s.jobs["source"] = source
    assert "Source job" in s.omni_extend_video("Continue", source_job_id="source")
    fake_client.interactions.create.assert_not_called()


def test_restored_tools_validate_paths_and_uri(fake_client, tmp_path):
    from omni_mcp_server.core.validation import ValidationError

    with pytest.raises(ValidationError):
        s.omni_extend_video("test", video_uri="https://169.254.169.254/metadata")
    with pytest.raises(ValidationError):
        s.omni_extend_video("test", video_uri="https://generativelanguage.googleapis.com/v1beta/files/source",
                           output_path=str(Path.home() / ".ssh" / "evil.mp4"))
    image = tmp_path / "image.png"
    image.write_bytes(b"fake")
    for first, last in [(str(image), "../../secret.png"), ("../../secret.png", str(image))]:
        with pytest.raises(ValidationError):
            s.omni_interpolate_video("test", first, last)
    with pytest.raises(ValidationError):
        s.omni_generate_video("test", reference_image_paths="../../secret.png")
    fake_client.interactions.create.assert_not_called()
