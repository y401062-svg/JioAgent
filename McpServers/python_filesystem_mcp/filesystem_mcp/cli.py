from __future__ import annotations

import argparse
import os
from typing import Sequence

from .lib.paths import set_allowed_directories
from .server import create_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filesystem-mcp",
        description="Secure filesystem MCP server for reading, writing, searching, diffing, and patching files.",
    )
    parser.add_argument("directories", nargs="*", help="Allowed root directories.")
    parser.add_argument("--allow-cwd", action="store_true", help="Allow current working directory as a root.")
    parser.add_argument("--port", type=int, help="Enable Streamable HTTP transport on the given port.")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    roots = list(args.directories)
    if args.allow_cwd:
        roots.append(os.getcwd())
    set_allowed_directories(roots)
    server = create_server(port=args.port)
    if args.port is not None:
        server.run(transport="streamable-http")
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
