"""Image model routing and FastMCP 4 compatibility, without network or keys."""
import asyncio
import io
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest
from fastmcp import Client
from PIL import Image

from nanobanana_mcp_server.config.settings import (
    AuthMethod, FlashImageConfig, GeminiConfig, ProImageConfig, ServerConfig,
)
from nanobanana_mcp_server.core.exceptions import AuthenticationError
from nanobanana_mcp_server.core.server import NanoBananaMCP
from nanobanana_mcp_server.services.gemini_client import GeminiClient
from nanobanana_mcp_server.services.file_image_service import FileImageService


@pytest.mark.parametrize("config,model", [
    (FlashImageConfig(), "gemini-nano-banana-2.1"),
    (ProImageConfig(), "gemini-3-pro-image"),
    (GeminiConfig(), "gemini-nano-banana-2.1"),
])
def test_fake_image_generation(config, model, tmp_path):
    server_config = ServerConfig(auth_method=AuthMethod.API_KEY, image_output_dir=str(tmp_path))
    wrapper = GeminiClient(server_config, config)
    fake = Mock()
    png = io.BytesIO()
    Image.new("RGB", (32, 24), "blue").save(png, format="PNG")
    fake.models.generate_content.return_value = NS(candidates=[NS(content=NS(parts=[
        NS(inline_data=NS(data=png.getvalue()))
    ]))])
    wrapper._client = fake
    service = FileImageService(wrapper, config, server_config)
    previews, metadata = service.generate_images("A blue square", aspect_ratio="4:3")
    assert len(previews) == len(metadata) == 1
    assert Path(metadata[0]["full_path"]).read_bytes() == png.getvalue()
    request = fake.models.generate_content.call_args.kwargs
    assert request["model"] == model
    assert request["config"].image_config.aspect_ratio == "4:3"
    assert wrapper.extract_images(fake.models.generate_content.return_value) == [png.getvalue()]


def test_missing_key_client_error():
    wrapper = GeminiClient(ServerConfig(auth_method=AuthMethod.API_KEY), GeminiConfig())
    with pytest.raises(AuthenticationError, match="GEMINI_API_KEY"):
        wrapper.generate_content(["test"])


def test_missing_key_configuration_error(monkeypatch):
    monkeypatch.setenv("NANOBANANA_AUTH_METHOD", "api_key")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        ServerConfig.from_env()


def test_mcp_tool_list():
    app = NanoBananaMCP(ServerConfig()).server

    async def check():
        async with Client(app) as client:
            tools = await client.list_tools()
            assert {tool.name for tool in tools} == {
                "generate_image", "upload_file", "show_output_stats", "maintenance",
            }
    asyncio.run(check())
