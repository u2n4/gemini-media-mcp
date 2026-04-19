"""
Nano Banana MCP Server - AI-powered image generation and editing via Nano Banana 2 + Pro.

A production-ready Model Context Protocol server built with FastMCP.
"""

try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("nanobanana-imagen-mcp")
    except PackageNotFoundError:
        __version__ = "0.0.0+local"
except ImportError:
    __version__ = "0.0.0+local"

__author__ = "Nano Banana Team"
__email__ = "team@nanobanana.dev"
__description__ = (
    "A production-ready MCP server for AI-powered image generation using Nano Banana 2 + Pro"
)

from .server import create_app, create_wrapper_app, main

__all__ = ["create_app", "create_wrapper_app", "main"]
