from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Sequence

from . import __version__
from .lib.state import BrowserConfig
from .server import create_server


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    config = BrowserConfig(
        browser_type=args.browser_type,
        headless=args.headless,
        isolated=args.isolated,
        user_data_dir=Path(args.user_data_dir).expanduser() if args.user_data_dir else None,
        viewport=parse_viewport(args.viewport_size),
        host=args.host,
        port=args.port,
        action_timeout_ms=args.timeout_action,
        navigation_timeout_ms=args.timeout_navigation,
        no_sandbox=args.no_sandbox,
        output_dir=Path(args.output_dir).expanduser() if args.output_dir else None,
        frame_selector=args.frame_selector,
    )
    server = create_server(config)
    server.run("streamable-http" if args.port else "stdio")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="playwright-mcp-python",
        description="Python Playwright MCP server. Defaults to stdio transport.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    browser = parser.add_mutually_exclusive_group()
    browser.add_argument("--browser", dest="browser_type", choices=["chromium", "firefox", "webkit", "chrome", "msedge"])
    browser.add_argument("--browser-type", dest="browser_type", choices=["chromium", "firefox", "webkit", "chrome", "msedge"])
    parser.set_defaults(browser_type="chromium")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode.")
    parser.add_argument("--isolated", action="store_true", help="Use an in-memory browser context instead of a persistent profile.")
    parser.add_argument("--user-data-dir", help="Persistent browser profile directory. Ignored when --isolated is set.")
    parser.add_argument("--viewport-size", help='Viewport size, for example "1280x720".')
    parser.add_argument("--host", default="127.0.0.1", help="Host for Streamable HTTP mode. Default: 127.0.0.1.")
    parser.add_argument("--port", type=int, help="Enable Streamable HTTP transport on this port. Omit for stdio.")
    parser.add_argument("--timeout-action", type=int, default=5000, help="Action timeout in milliseconds. Default: 5000.")
    parser.add_argument("--timeout-navigation", type=int, default=60000, help="Navigation timeout in milliseconds. Default: 60000.")
    parser.add_argument("--no-sandbox", action="store_true", help="Pass --no-sandbox to Chromium-based launches.")
    parser.add_argument(
        "--output-dir",
        default=os.environ.get("PLAYWRIGHT_MCP_OUTPUT_DIR"),
        help="Directory used for relative observability output filenames. Env: PLAYWRIGHT_MCP_OUTPUT_DIR.",
    )
    parser.add_argument(
        "--frame-selector",
        default=os.environ.get("PLAYWRIGHT_MCP_FRAME_SELECTOR"),
        help="Scope selector-based actions to a frame, for example '#iframeResult'. Env: PLAYWRIGHT_MCP_FRAME_SELECTOR.",
    )
    return parser


def parse_viewport(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    parts = value.lower().split("x", 1)
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("--viewport-size must look like 1280x720")
    try:
        width, height = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--viewport-size must contain integer width and height") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("--viewport-size must be positive")
    return width, height
