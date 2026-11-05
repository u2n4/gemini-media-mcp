"""Reproductions of current fleet defects, with fake clients and local fixtures."""

import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace as NS
from unittest.mock import Mock

from fastmcp import Client, FastMCP
from PIL import Image
import pytest

from nanobanana_mcp_server.config.settings import GeminiConfig, ServerConfig, ModelSelectionConfig, ProImageConfig
from nanobanana_mcp_server.core.exceptions import FileOperationError, ValidationError
from nanobanana_mcp_server.core.progress_tracker import ProgressTracker
from nanobanana_mcp_server.core.validation import validate_file_path, validate_input_image
from nanobanana_mcp_server.services.enhanced_image_service import EnhancedImageService
from nanobanana_mcp_server.services.file_image_service import FileImageService
from nanobanana_mcp_server.services.file_service import FileService
from nanobanana_mcp_server.services.files_api_service import FilesAPIService
from nanobanana_mcp_server.services.image_database_service import ImageDatabaseService
from nanobanana_mcp_server.services.image_service import ImageService
from nanobanana_mcp_server.services.image_storage_service import ImageStorageService
from nanobanana_mcp_server.services.gemini_client import GeminiClient
from nanobanana_mcp_server.services.maintenance_service import MaintenanceService
from nanobanana_mcp_server.services.pro_image_service import ProImageService
from nanobanana_mcp_server.utils.validation_utils import validate_output_path, validate_positive_integer, sanitize_filename
from nanobanana_mcp_server.utils.image_utils import convert_image_format


def png(mode="RGB"):
    output = BytesIO()
    Image.new(mode, (32, 32), 0).save(output, "PNG")
    return output.getvalue()


def test_absolute_relative_and_dotted_files(tmp_path, monkeypatch):
    image = tmp_path / "image..png"
    image.write_bytes(png())
    assert validate_file_path(str(image)) == image
    assert validate_file_path(image.as_posix()) == image
    monkeypatch.chdir(tmp_path)
    assert validate_file_path(image.name) == image


@pytest.mark.parametrize("path", ["../image.png", "dir/../image.png", r"dir\..\image.png",
    "/etc/passwd", "//etc/passwd", r"C:\Windows\image.png", r"\\?\C:\Windows\image.png",
    "~/.ssh/key.png", "~/.aws/credentials", "~/.config/gcloud/key.png", "x\x00.png"])
def test_sensitive_and_traversal_paths(path):
    with pytest.raises(ValidationError):
        validate_file_path(path)


def test_symlink_to_sensitive_file(tmp_path):
    secret = tmp_path / ".ssh" / "key.png"
    secret.parent.mkdir()
    secret.write_bytes(png())
    link = tmp_path / "innocent.png"
    try:
        link.symlink_to(secret)
    except OSError:
        pytest.skip("OS does not permit creating symlinks")
    with pytest.raises(ValidationError, match="protected"):
        validate_file_path(str(link))


def test_image_content_and_size(tmp_path):
    image = tmp_path / "fake.png"
    image.write_text("This is not an image")
    with pytest.raises(ValidationError, match="valid supported image"):
        validate_input_image(str(image))
    image.write_bytes(png())
    assert validate_input_image(str(image))[1] == "image/png"
    with image.open("wb") as f:
        f.truncate(20 * 1024 * 1024 + 1)
    with pytest.raises(ValidationError, match="20 MiB"):
        validate_input_image(str(image))


def test_tilde_config_and_invalid_enums(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("IMAGE_OUTPUT_DIR", "~/pictures")
    assert ServerConfig.from_env().image_output_dir == str(tmp_path / "pictures")
    monkeypatch.setenv("NANOBANANA_AUTH_METHOD", "typo")
    with pytest.raises(ValueError, match="NANOBANANA_AUTH_METHOD"):
        ServerConfig.from_env()
    monkeypatch.setenv("NANOBANANA_MODEL", "typo")
    with pytest.raises(ValueError, match="NANOBANANA_MODEL"):
        ModelSelectionConfig.from_env()


@pytest.mark.parametrize("value", [True, False, 1.5, "1"])
def test_positive_integer_is_strict(value):
    with pytest.raises(ValidationError):
        validate_positive_integer(value, "count")


def test_output_protection_and_boundary(tmp_path):
    with pytest.raises(ValidationError):
        validate_output_path(str(tmp_path / ".ssh" / "image.png"))
    validate_output_path("/etc-images/picture.png")
    assert sanitize_filename("CON.png") == "_CON.png"
    assert "\x00" not in sanitize_filename("x\x00.png")


def test_filenames_reserved_atomically(tmp_path):
    service = FileImageService(Mock(), GeminiConfig(), ServerConfig(image_output_dir=str(tmp_path)))
    with ThreadPoolExecutor(max_workers=4) as pool:
        names = list(pool.map(lambda _: service._get_next_filename(), range(12)))
    assert len(set(names)) == 12
    assert all((tmp_path / name).exists() for name in names)
    with pytest.raises(ValidationError):
        service._get_next_filename("../escape")


@pytest.mark.parametrize("mode", ["RGBA", "LA"])
def test_transparent_thumbnails_white(tmp_path, mode):
    service = ImageStorageService(GeminiConfig(), str(tmp_path))
    thumbnail, _, _ = service._generate_thumbnail(png(mode), "image/png")
    assert min(Image.open(BytesIO(thumbnail)).getpixel((0, 0))) > 245
    converted = convert_image_format(base64.b64encode(png(mode)).decode(), "JPEG")
    assert min(Image.open(BytesIO(base64.b64decode(converted))).getpixel((0, 0))) > 245


def test_corrupt_registry_preserved(tmp_path):
    registry = tmp_path / "image_registry.json"
    registry.write_text("broken JSON")
    with pytest.raises(json.JSONDecodeError):
        ImageStorageService(GeminiConfig(), str(tmp_path))
    assert registry.read_text() == "broken JSON"


def test_registry_replace_failure_preserves_previous_file(tmp_path, monkeypatch):
    service = ImageStorageService(GeminiConfig(), str(tmp_path))
    service.store_image(png(), "image/png")
    previous = service.metadata_file.read_bytes()
    monkeypatch.setattr("os.replace", Mock(side_effect=PermissionError("fake replacement failure")))
    with pytest.raises(PermissionError, match="fake replacement"):
        service._save_registry()
    assert service.metadata_file.read_bytes() == previous


def test_storage_returns_images_even_without_thumbnails(tmp_path):
    client = Mock()
    client.create_image_parts.return_value = []
    client.extract_images.return_value = [png()]
    storage = ImageStorageService(GeminiConfig(), str(tmp_path))
    storage.get_thumbnail_base64 = Mock(return_value=None)
    legacy = ImageService(client, GeminiConfig(), storage)
    edited, count = legacy.edit_image("blue", base64.b64encode(png()).decode())
    assert count == 1 and edited[0].data == png()
    for service in (legacy, ProImageService(client, ProImageConfig(), storage)):
        previews, metadata = service.generate_images("blue")
        assert len(previews) == len(metadata) == 1
        assert previews[0].data == png()


def test_partial_batch_failure_is_visible(tmp_path):
    client = Mock()
    client.generate_content.side_effect = [Mock(), RuntimeError("fake second request failure")]
    client.extract_images.return_value = [png()]
    service = FileImageService(client, GeminiConfig(), ServerConfig(image_output_dir=str(tmp_path)))
    with pytest.raises(RuntimeError, match="second request"):
        service.generate_images("blue", n=2)


def test_registry_paths_and_expiry_persistence(tmp_path):
    service = ImageStorageService(GeminiConfig(), str(tmp_path / "storage"))
    info = service.store_image(png(), "image/png")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"private")
    original = info.full_path
    info.full_path = str(outside)
    assert service.get_image_bytes(info.id) is None
    assert not service.delete_image(info.id)
    assert outside.read_bytes() == b"private"
    info.full_path = original
    info.expires_at = 0
    service._cleanup_expired()
    assert json.loads(service.metadata_file.read_text()) == {}


def insert(db, path="missing", expires_at=None):
    return db.upsert_image(path, "missing-thumb", "image/png", 32, 32, 10,
                           file_id="files/test", expires_at=expires_at)


def test_database_writers_expiry_dry_run_and_close(tmp_path):
    db_path = str(tmp_path / "images.db")
    dbs = [ImageDatabaseService(db_path), ImageDatabaseService(db_path)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(lambda db: insert(db), dbs))
    assert ids[0] == ids[1]
    db = dbs[0]
    assert db.get_usage_stats()["total_images"] == 1
    assert db.cleanup_missing_files(dry_run=True) == 1
    assert db.get_by_id(ids[0]) is not None
    expires = datetime.now(timezone(timedelta(hours=8))) - timedelta(seconds=10)
    assert db.update_files_api_info(ids[0], "files/test", "uri", expires)
    assert len(db.list_expired_files(buffer_minutes=0)) == 1
    with db._conn() as conn:
        conn.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        conn.execute("SELECT 1")


def test_file_sizes_missing_and_processing_state():
    client = Mock()
    client.client.files.list.return_value = [NS(name="files/test", uri="uri", mime_type=None, size_bytes=None)]
    service = FileService(client)
    assert service.get_file_usage_stats()["file_types"] == {"unknown": {"count": 1, "total_size_bytes": 0}}
    client.get_file_metadata.return_value = NS(state="PROCESSING")
    files = FilesAPIService(client, Mock())
    with pytest.raises(FileOperationError, match="still processing"):
        files.ensure_file_available("files/test")
    client.upload_file.assert_not_called()


def test_upload_reports_pending_state(tmp_path):
    image = tmp_path / "image.png"
    image.write_bytes(png())
    client = Mock()
    client.upload_file.return_value = NS(name="files/pending", uri=None, state="PROCESSING", size_bytes=None)
    metadata = FileService(client).upload_file(str(image))
    assert metadata["state"] == "PROCESSING"
    assert metadata["ready"] is False
    assert metadata["size_bytes"] == len(png())


def test_tracking_failure_is_not_success(tmp_path):
    image = tmp_path / "image.png"
    image.write_bytes(png())
    client, db = Mock(), Mock()
    client.upload_file.return_value = NS(name="files/test", uri="uri")
    db.update_files_api_info.return_value = False
    with pytest.raises(FileOperationError, match="database record"):
        FilesAPIService(client, db).upload_and_track(str(image), record_id=1)


def test_progress_terminal_states_keep_last_percentage():
    tracker = ProgressTracker()
    for terminal in (tracker.fail_operation, tracker.cancel_operation):
        operation = tracker.start_operation("image_generation")
        tracker.update_progress(operation, 70, "working")
        terminal(operation, "stopped")
        assert tracker.get_operation_status(operation)["progress_percent"] == 70
        assert tracker.get_operation(operation).updates[-1].progress_percent == 70


def test_edit_creates_directory_and_generation_preserves_failure(tmp_path):
    client, files, db = Mock(), Mock(), Mock()
    files.upload_and_track.return_value = ("files/test", "uri")
    db.upsert_image.return_value = 1
    service = EnhancedImageService(client, files, db, GeminiConfig(), str(tmp_path / "new"))
    _, meta = service._process_edited_image(png(), "blue", None, 1)
    assert Path(meta["full_path"]).read_bytes() == png()
    client.generate_content.side_effect = RuntimeError("fake API failure")
    for generator in (service, ImageService(client, GeminiConfig())):
        with pytest.raises(RuntimeError, match="fake API failure"):
            generator.generate_images("a blue square")


def test_variable_image_counts_use_unique_indices(tmp_path):
    client = Mock()
    client.extract_images.side_effect = [[b"a", b"b"], [b"c"]]
    service = EnhancedImageService(client, Mock(), Mock(), GeminiConfig(), str(tmp_path))
    service._process_generated_image = Mock(return_value=(Mock(), {"full_path": "fake"}))
    service.generate_images("blue", n=2, output_path=str(tmp_path / "result.png"), resolution="4k")
    assert [c.kwargs["image_index_for_path"] for c in service._process_generated_image.call_args_list] == [1, 2, 3]
    assert client.generate_content.call_args.kwargs["config"] == {"resolution": "4k"}


def test_flash_resolution_uses_real_sdk_image_config():
    from nanobanana_mcp_server.config.settings import FlashImageConfig

    wrapper = GeminiClient(ServerConfig(), FlashImageConfig())
    wrapper._client = Mock()
    wrapper.generate_content(["blue"], config={"resolution": "4k"}, aspect_ratio="16:9")
    config = wrapper._client.models.generate_content.call_args.kwargs["config"]
    assert config.image_config.image_size == "4K"
    assert config.image_config.aspect_ratio == "16:9"


def test_generation_replaces_existing_output_on_windows(tmp_path):
    files, db = Mock(), Mock()
    files.upload_and_track.return_value = ("files/test", "uri")
    db.upsert_image.return_value = 1
    service = EnhancedImageService(Mock(), files, db, GeminiConfig(), str(tmp_path))
    args = (png(), 1, 1, "blue", None, None, None)
    target = tmp_path / "result.png"
    service._process_generated_image(*args, output_path=str(target))
    service._process_generated_image(*args, output_path=str(target))
    assert target.read_bytes() == png()


def test_cleanup_keeps_referenced_thumbnail_and_counts_dry_run(tmp_path):
    import os
    import time

    db = ImageDatabaseService(":memory:")
    main, thumb = tmp_path / "main.png", tmp_path / "main_thumb.jpeg"
    main.write_bytes(png())
    thumb.write_bytes(b"thumbnail")
    old = time.time() - 3600 * 48
    for path in (main, thumb):
        os.utime(path, (old, old))
    db.upsert_image(str(main), str(thumb), "image/png", 32, 32, len(png()), file_id="files/test")
    service = MaintenanceService(Mock(), db, str(tmp_path))
    result = service.cleanup_local_files(dry_run=False, max_age_hours=1, keep_count=0)
    assert result["total_files"] == 1
    assert result["removed_count"] == 0
    assert result["errors"] == []
    assert main.exists() and thumb.exists()
    missing = insert(db)
    result = service.database_hygiene(dry_run=True)
    assert result["missing_files_removed"] == 1
    assert db.get_by_id(missing) is not None


def test_generate_annotation_and_resource_dict_support():
    from nanobanana_mcp_server.tools.generate_image import register_generate_image_tool
    app = FastMCP("test")
    register_generate_image_tool(app)

    @app.resource("test://dictionary")
    def dictionary():
        return {"supported": True}

    async def check():
        async with Client(app) as client:
            tool = (await client.list_tools())[0]
            assert tool.annotations.read_only_hint is False
            assert json.loads((await client.read_resource("test://dictionary"))[0].text) == {"supported": True}
    asyncio.run(check())
