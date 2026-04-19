"""VEO MCP Server -- 4K video generation with Google VEO 3.1."""

try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("veo-mcp-server")
    except PackageNotFoundError:
        __version__ = "0.0.0+local"
except ImportError:
    __version__ = "0.0.0+local"

from .server import main

__all__ = ["main"]
