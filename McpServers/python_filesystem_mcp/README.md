# Python Filesystem MCP Server

This folder is the distributable Python package for the secure filesystem MCP server. It is intended to be registered directly in an MCP client and run with `python -m filesystem_mcp` or the installed console script.

The original Node.js/TypeScript implementation remains the oracle in the source repository. This package contains only the Python runtime files needed to run the Python MCP server, plus user-facing setup and smoke-check helpers.

## Contents

- `pyproject.toml` - Python package metadata, dependencies, and console scripts.
- `filesystem_mcp/` - Python MCP server runtime.
- `mcp-server.example.json` - MCP client registration example.
- `scripts/smoke_python_package.py` - import and CLI help smoke check for this package folder.

Test suites, parity harnesses, `node_modules`, Node build output, and draft docs are intentionally excluded.

## Requirements

- Python 3.11 or newer
- Python package dependencies from `pyproject.toml`:
  - `mcp>=1.0.0`
  - `pydantic>=2.0.0`

## Installation

From this package directory:

```powershell
python -m pip install .
```

For an isolated environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .
```

You can also run from source without installing if your MCP client sets `cwd` to this package directory and uses `python -m filesystem_mcp`.

## Running

Run over stdio, which is the default MCP transport:

```powershell
python -m filesystem_mcp D:\allowed\workspace
```

After installation, either console script works:

```powershell
filesystem-mcp-python D:\allowed\workspace
filesystem-mcp D:\allowed\workspace
```

Allow the current working directory as a root:

```powershell
python -m filesystem_mcp --allow-cwd
```

Allow multiple roots:

```powershell
python -m filesystem_mcp D:\allowed\workspace C:\Users\you\Documents\project
```

## HTTP Mode

Use `--port` to start Streamable HTTP transport instead of stdio:

```powershell
python -m filesystem_mcp --port 8000 D:\allowed\workspace
```

The HTTP MCP endpoint is served at `/mcp` on the configured port.

## MCP Client Registration

Use an absolute `cwd` that points to this package directory if running from source:

```json
{
  "mcpServers": {
    "filesystem-mcp-python": {
      "command": "python",
      "args": [
        "-m",
        "filesystem_mcp",
        "D:\\allowed\\workspace"
      ],
      "cwd": "D:\\src\\MCP\\filesystem-mcp-main\\filesystem-mcp-main\\release\\python-filesystem-mcp"
    }
  }
}
```

If the package is installed into the Python environment used by the client, `cwd` is optional:

```json
{
  "mcpServers": {
    "filesystem-mcp-python": {
      "command": "filesystem-mcp-python",
      "args": ["D:\\allowed\\workspace"]
    }
  }
}
```

## Allowed Roots

Allowed roots are the positional directory arguments passed after the module name or command. The server rejects file operations outside these roots, including path traversal and symlink escapes.

Examples:

```powershell
python -m filesystem_mcp D:\work\repo
python -m filesystem_mcp C:\Users\you\Documents\project D:\shared\readonly
```

Use only the smallest directory set your MCP client needs.

## Security Restrictions

- File access is constrained to configured allowed roots.
- Paths outside allowed roots are blocked.
- Symlink escapes outside allowed roots are blocked during path validation.
- Sensitive file patterns are denied by default, including `.env`, `.env.*`, `.npmrc`, `.pypirc`, AWS credential files, private keys, certificates, and related token files.
- `FS_CONTEXT_DENYLIST` can add deny patterns.
- `FS_CONTEXT_ALLOWLIST` can allow specific sensitive patterns.
- `FS_CONTEXT_ALLOW_SENSITIVE=1` disables the default sensitive-file denylist; use only in controlled environments.

## Smoke Checks

From this package directory:

```powershell
python -m filesystem_mcp --help
python scripts\smoke_python_package.py
```

From the original repository, run the full Python validation suite:

```powershell
python -m filesystem_mcp --help
python -B -m unittest discover -s tests_python
```

`tests_python` is intentionally not included in this distributable package; it belongs to the source repository validation workflow.

## Troubleshooting

### Show CLI Help

```powershell
python -m filesystem_mcp --help
```

### Import Failure

Install dependencies and confirm you are using Python 3.11 or newer:

```powershell
python --version
python -m pip install .
```

If running from source, set the MCP client's `cwd` to this package directory so Python can import `filesystem_mcp`.

### Wrong Working Directory

If your MCP client reports `No module named filesystem_mcp`, either install the package in that client's Python environment or set `cwd` to the folder containing `pyproject.toml` and `filesystem_mcp/`.

### Missing Dependencies

Install package dependencies:

```powershell
python -m pip install .
```

For editable local testing:

```powershell
python -m pip install -e .
```

### Allowed Root Errors

Pass at least one allowed root or use `--allow-cwd`:

```powershell
python -m filesystem_mcp D:\allowed\workspace
python -m filesystem_mcp --allow-cwd
```
