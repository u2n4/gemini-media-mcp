"""Omni MCP Server -- video generation with Gemini Omni."""

try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("omni-mcp-server")
    except PackageNotFoundError:
        __version__ = "0.0.0+local"
except ImportError:
    __version__ = "0.0.0+local"

from .server import main

__all__ = ["main"]
