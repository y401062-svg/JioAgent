from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .browser import BrowserManager
from .lib.state import BrowserConfig
from .tools import register_tools


def create_server(config: BrowserConfig | None = None) -> FastMCP:
    config = config or BrowserConfig()
    server = FastMCP(
        "Python Playwright MCP",
        instructions="Browser automation MCP server implemented with Python Playwright.",
        host=config.host,
        port=config.port or 8000,
        streamable_http_path="/mcp",
    )
    register_tools(server, BrowserManager(config))
    return server
