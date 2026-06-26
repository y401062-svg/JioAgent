---
name: external-mcp-server-setup
description: Guidance for adding, editing, validating, and activating external MCP server manifests for AgentConsole.
category: agent
tags: [agent, mcp, external-mcp, setup, manifest]
---

# External MCP Server Setup

Use this skill when the user wants to add, modify, troubleshoot, or validate an external MCP server for AgentConsole. This skill is operational guidance only; do not install MCP servers or copy test MCP servers into deployment unless the user explicitly asks for that separate work.

## Manifest Locations

For deployment, place each external MCP server manifest at:

```text
deploy/JioAgent/McpServers/<server-id>/mcp-server.json
```

Also place the deployable MCP server runtime under the same server folder whenever possible:

```text
deploy/JioAgent/McpServers/<server-id>/
```

Keep the server source, build output, executable entry point, required `node_modules`, and other runtime files self-contained under that folder. This makes the deployed `JioAgent` folder portable and avoids depending on a developer's Downloads, Desktop, temporary folder, user profile, or drive-specific external path.

For development, place each manifest at one of these locations:

```text
<repo>/McpServers/<server-id>/mcp-server.json
```

or under the folder passed to AgentConsole with:

```powershell
--mcp-servers-root D:\path\to\McpServers
```

AgentConsole discovers `mcp-server.json` files recursively under the configured MCP servers root.

## Manifest Shape

Use this base structure:

```json
{
  "id": "server-id",
  "name": "Readable Server Name",
  "description": "What this MCP server exposes.",
  "transport": "stdio",
  "command": "command-name",
  "args": [],
  "env": {},
  "workingDirectory": ".",
  "stdioTimeoutSeconds": 5,
  "tags": [
    "stdio"
  ]
}
```

Fields:

- `id`: stable server id. Prefer lowercase letters, digits, and hyphens. If omitted, AgentConsole uses the manifest folder name.
- `name`: readable display name. Defaults to `id`.
- `description`: short explanation for users and future agent context.
- `transport`: currently use `stdio`.
- `command`: executable command such as `node`, `npx`, or a local `.exe`.
- `args`: command arguments as a JSON array. Keep each argument as one array item.
- `env`: per-process environment variables. Use environment variable names or non-secret configuration here.
- `workingDirectory`: optional process working directory. Prefer `"."`. Relative values are resolved from the folder containing this `mcp-server.json`.
- `stdioTimeoutSeconds`: optional stdio JSON-RPC response timeout for `initialize`, `tools/list`, and `tools/call`. Defaults to `5`; valid values are `1` through `600`.
- `tags`: labels such as `node`, `npx`, `filesystem`, `local`, or `stdio`.

Use a longer `stdioTimeoutSeconds` only when the server can realistically respond after slower startup or synchronous preparation work. It is not a universal fix for a blocked MCP server or an event loop that cannot read/write protocol messages. Longer values can tie up the active JioAgent turn for that many seconds before timeout, so keep ordinary servers near the default and raise it only for known slow operations.

New manifests only make servers discoverable. The server is not exposed to the model until the user enables it with `/mcp select`, the control API, runtime config `activeMcpServerIds`, or launch args such as `--activate-mcp-server <id>`.

Before proposing a manifest, consider that users may run many AgentConsole instances at the same time. Each AgentConsole process has its own MCP runtime registry and can start its own copy of every active external MCP server. Classify the server's concurrency behavior before finalizing `args`, `env`, and `workingDirectory`:

- **Multi-process safe**: the server is read-only or uses only process-local state. A normal manifest is acceptable.
- **Path/cache/profile/socket sensitive**: the server can run multiple copies, but only if writable paths are separated per AgentConsole process. Use manifest runtime tokens in `args` or `env` for every mutable path.
- **Singleton only**: the server uses a fixed port, global lock, single-user database, device handle, or another exclusive resource that cannot be separated by configuration. Do not pretend the manifest alone makes it safe. Warn the user and recommend deactivating it in extra AgentConsole instances, adding JioAgent-level exclusive-lock support, or placing a single broker/proxy MCP process in front of it.
- **Shared service**: the server is intentionally a client for a remote database, HTTP service, or daemon that safely handles concurrent clients. Keep the MCP process stateless where possible and put shared state in the external service.

When a server writes local state, prefer per-process paths with these supported runtime tokens:

```json
{
  "env": {
    "MCP_DATA_DIR": "{tempPath}\\JioAgent\\McpServers\\{serverId}\\pid-{processId}\\data",
    "MCP_CACHE_DIR": "{tempPath}\\JioAgent\\McpServers\\{serverId}\\pid-{processId}\\cache"
  }
}
```

Token meanings:

- `{tempPath}`: OS temp directory.
- `{serverId}`: file-name-safe MCP server id.
- `{processId}`: current AgentConsole process id.
- `{workingDirectory}`: resolved server working directory.

Use these tokens for database folders, browser profiles, socket directories, output folders, lock files that are meant to be process-local, temporary downloads, and debug logs. Do not use a shared writable folder such as `%USERPROFILE%\.server-name`, `Downloads`, or a fixed database path unless the server documentation says concurrent access is safe.

Example for a Python/KuzuDB-based MCP server such as CodeGraphContext:

```json
{
  "id": "codegraphcontext-mcp",
  "name": "CodeGraphContext",
  "description": "Code graph analysis MCP server with per-AgentConsole KuzuDB storage.",
  "transport": "stdio",
  "command": "codegraphcontext",
  "args": [
    "mcp",
    "start"
  ],
  "env": {
    "CGC_ALLOWED_ROOTS": "D:\\",
    "DEFAULT_DATABASE": "kuzudb",
    "KUZUDB_PATH": "{tempPath}\\JioAgent\\McpServers\\{serverId}\\pid-{processId}\\kuzudb",
    "DEBUG_LOG_PATH": "{tempPath}\\JioAgent\\McpServers\\{serverId}\\pid-{processId}\\mcp_debug.log"
  },
  "workingDirectory": "D:\\src\\jio_agent\\jio_agent",
  "stdioTimeoutSeconds": 120,
  "tags": [
    "python",
    "stdio",
    "code-graph",
    "kuzudb",
    "per-process"
  ]
}
```

This prevents file-lock collisions between AgentConsole processes, but each process gets its own graph database. If the user needs all AgentConsole instances to share one graph, say that a shared service or broker/lock design is required rather than silently pointing all instances at the same local KuzuDB folder.

For deployed servers, the default is to keep `workingDirectory` as `"."`, meaning the process starts from `deploy/JioAgent/McpServers/<server-id>/`. If the server must run from a subfolder, use only a relative path inside that server folder, such as `"runtime"`, `"server"`, or `"dist"`.

Avoid absolute `workingDirectory` values that point to a user account, Downloads, Desktop, temporary folder, or a specific external drive location. Only propose an absolute working directory when the server source/runtime cannot be copied because of licensing, size, or installation constraints. Before using an absolute path, explicitly ask the user for approval and warn that it is not portable and can break when:

- files or folders move;
- Downloads or temporary folders are cleaned;
- the Windows user account name changes;
- the deployment is copied to another PC;
- drive letters change;
- permissions change;
- `node_modules` or build output is deleted;
- an external server update changes the executable or entry point.

If an absolute path is used after user approval, include in the work summary that the MCP server is not portable and will not run if that path disappears.

## Examples

Minimal stdio server:

```json
{
  "id": "local-tools",
  "name": "Local Tools",
  "description": "Local stdio MCP server.",
  "transport": "stdio",
  "command": "node",
  "args": [
    "server.js"
  ],
  "env": {},
  "workingDirectory": ".",
  "tags": [
    "node",
    "stdio"
  ]
}
```

Node.js/npx server:

```json
{
  "id": "filesystem",
  "name": "Filesystem",
  "description": "Filesystem MCP server launched with npx.",
  "transport": "stdio",
  "command": "npx",
  "args": [
    "-y",
    "@modelcontextprotocol/server-filesystem",
    "D:\\src\\jio_agent\\jio_agent"
  ],
  "env": {},
  "workingDirectory": ".",
  "tags": [
    "node",
    "npx",
    "filesystem",
    "stdio"
  ]
}
```

Local executable server:

```json
{
  "id": "company-tools",
  "name": "Company Tools",
  "description": "Internal MCP server packaged under this server folder.",
  "transport": "stdio",
  "command": "runtime\\CompanyMcpServer.exe",
  "args": [
    "--stdio",
    "--config",
    "config\\company-tools.json"
  ],
  "env": {
    "COMPANY_MCP_PROFILE": "local"
  },
  "workingDirectory": "runtime",
  "tags": [
    "local",
    "exe",
    "stdio"
  ]
}
```

## Windows And Secret Handling

In JSON, escape Windows backslashes as `\\`. For example, write `D:\\tools\\server.exe`, not `D:\tools\server.exe`.

Prefer one argument per `args` entry. Do not combine a command and its arguments into one string unless the executable itself expects that exact string.

Do not put API keys, tokens, passwords, or other secrets directly in `mcp-server.json`. Prefer machine/user environment variables, Windows credential storage, or another secure configuration mechanism supported by that MCP server. If a server needs an environment variable name, put the variable name in the manifest and set the secret outside the manifest.

## AgentConsole Verification

After adding or changing a manifest, restart AgentConsole so startup discovery reads the latest MCP server list. If AgentConsole is already running and the server was previously started, restart is the clearest way to avoid stale process state.

Then run:

```text
/mcp servers
/mcp tools <server-id>
/mcp select
/tools
```

Expected checks:

- `/mcp servers` lists the configured manifest and status.
- `/mcp tools <server-id>` starts or reuses the stdio process, runs `initialize`, calls `tools/list`, and prints model-facing tool names.
- `/mcp select` lets the user activate or deactivate the server for future model turns.
- `/tools` shows built-in tools plus active external MCP tools exposed to the model.
- The server starts directly from `deploy/JioAgent/McpServers/<server-id>/` with `workingDirectory` set to `"."` or to a relative subfolder inside that server folder.

If discovery or tool listing fails, check:

- `command` exists on `PATH` or uses a correct absolute path.
- `args` are split correctly and match the server documentation.
- `workingDirectory` exists after resolving relative to the manifest folder, and deployed manifests do not rely on an absolute external folder unless the user approved that non-portable exception.
- `env` contains required non-secret settings and required secrets are available through the real environment.
- Node.js is installed and available on `PATH` for `node` or `npx` manifests.
- The server writes JSON-RPC protocol messages to stdout and sends logs/errors to stderr. Extra non-protocol stdout text can break stdio MCP communication.
- The server can start manually from the same working directory with the same command, args, and environment.
