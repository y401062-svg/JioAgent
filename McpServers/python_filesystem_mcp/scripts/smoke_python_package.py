from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path


def main() -> int:
    package_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(package_root))

    importlib.import_module("filesystem_mcp")
    importlib.import_module("filesystem_mcp.cli")
    importlib.import_module("filesystem_mcp.server")

    result = subprocess.run(
        [sys.executable, "-m", "filesystem_mcp", "--help"],
        cwd=package_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode
    if "Allowed root directories" not in result.stdout:
        sys.stderr.write(result.stdout)
        sys.stderr.write("\nCLI help did not include the expected allowed-root text.\n")
        return 1

    print("Python filesystem MCP package smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
