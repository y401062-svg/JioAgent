# Python Playwright MCP

This directory contains a separate Python implementation of a Playwright MCP server. The existing Node package `@playwright/mcp` in this repository is the oracle and remains unchanged. This Python package does not claim full parity; it implements a focused, verified deployment-candidate surface for users who can run Python but cannot run Node.js.

Current default-tool coverage: 22 of the Node oracle's 23 default tools are registered. The only missing default tool is `browser_run_code_unsafe`, which is intentionally not implemented because it executes arbitrary unsafe code.

## Install

From this repository root:

```powershell
python -m pip install .
python -m playwright install chromium
```

For source-tree execution without installing:

```powershell
python -m pip install mcp playwright pydantic
python -m playwright install chromium
python -m playwright_mcp --help
```

## Run

Default transport is stdio:

```powershell
python -m playwright_mcp --headless
```

Streamable HTTP mode is enabled by `--port`:

```powershell
python -m playwright_mcp --headless --port 8931
```

The Node oracle documents `--port` as SSE transport. This Python implementation uses the Python MCP SDK's Streamable HTTP transport at `/mcp`.

## MCP Client Registration

Use `mcp-server.example.json` as a starting point:

```json
{
  "mcpServers": {
    "playwright-mcp-python": {
      "command": "python",
      "args": ["-m", "playwright_mcp", "--headless"],
      "cwd": "D:\\src\\MCP\\playwright-mcp-main\\playwright-mcp-main"
    }
  }
}
```

If installed into a virtual environment, point `command` to that environment's Python executable or keep `cwd` set to the source/package directory.

## Deployment Readiness Scope

This Python server is suitable for deployment candidates that need the supported stdio tool surface below and accept the documented differences from the Node oracle. It is not a drop-in 1:1 replacement for `@playwright/mcp`.

Before promoting a copied deployment package, verify:

- `python -m playwright_mcp --help` succeeds from the source package root.
- `python -m playwright_mcp --help` succeeds from the deployment parent directory with `PYTHONPATH` pointed at that parent directory when the package is copied rather than installed.
- Source and deployment `.py` files have matching hashes.
- `python -B -m unittest discover -s tests_python` passes from the repository root.
- The baseline guard reports 22 Python source tools, 22 deployment tools, and only `browser_run_code_unsafe` missing from the Node default set.
- Any embedding MCP manifest describes stdio as the default transport and the supported tool surface without claiming Node 1:1 parity.

## Supported CLI Options

| Option | Python status | Notes |
| --- | --- | --- |
| `--headless` | Supported | Headed is the default, matching the Node README. |
| `--browser`, `--browser-type` | Supported | `chromium`, `firefox`, `webkit`, `chrome`, `msedge`. Chrome/Edge use Chromium channels. |
| `--isolated` | Supported | Uses a non-persistent context. |
| `--user-data-dir` | Supported | Uses persistent context when not isolated. |
| `--viewport-size` | Supported | Format: `1280x720`. |
| `--port` | Supported with difference | Enables Streamable HTTP, not Node oracle SSE. |
| `--host` | Supported | Applies to HTTP mode. |
| `--timeout-action`, `--timeout-navigation` | Supported | Milliseconds. |
| `--no-sandbox` | Supported | Chromium launch arg. |
| `--output-dir` | Supported with limited scope | Also reads `PLAYWRIGHT_MCP_OUTPUT_DIR`. Relative explicit output filenames/paths for observability, snapshot, and screenshot tools resolve under this directory. |
| Other Node README options | Not implemented | Examples: caps, config files, proxy, CDP/remote endpoints, storage state, allowed/blocked origins, unrestricted file access, permissions, device/user agent, save session, secrets, and output mode. |

## Implemented Tools

All tools return structured dictionaries. Success uses `{"ok": true, ...}` and failures use `{"ok": false, "error": {"code": "...", "message": "..."}}`.

| Tool | Status | Notes |
| --- | --- | --- |
| `browser_navigate` | Implemented | Navigates and returns a text page summary. `data:text/html` URLs are loaded with `set_content` instead of `goto` to avoid navigation hangs. |
| `browser_navigate_back` | Implemented | Goes back in browser history and returns a text page summary. |
| `browser_snapshot` | Implemented with difference | Text/DOM summary from `body.innerText`; not the Node oracle accessibility tree. Optional `filename` writes the structured payload as JSON. Node schema also supports `target`, `depth`, and `boxes`; Python does not implement those because they depend on Node snapshot refs/accessibility rendering. |
| `browser_click` | Implemented | Uses Playwright selectors. |
| `browser_hover` | Implemented | Hovers a selector or target. |
| `browser_select_option` | Implemented | Selects option values for a target. |
| `browser_fill_form` | Implemented | Fills a list of fields. Select elements are handled with `select_option` automatically. |
| `browser_file_upload` | Implemented | Uploads one or more file paths through a file chooser. |
| `browser_handle_dialog` | Implemented | Accepts or dismisses the next dialog; optional prompt text is supported. |
| `browser_drag` | Implemented | Drags from one target to another. |
| `browser_drop` | Implemented | Drops file paths or text data on a target. |
| `browser_type` | Implemented | Fills text into a selector; optional submit. |
| `browser_press_key` | Implemented | Page keyboard or selector-scoped press. |
| `browser_evaluate` | Implemented with difference | Evaluates JavaScript in the page. Accepts legacy `expression` and Node-style `function`; if both are supplied with different values, Python returns a structured error. Optional `filename` writes the structured `{"result": ...}` payload as JSON. Node schema also supports optional `target`/`element`; Python does not implement element-target evaluation. |
| `browser_resize` | Implemented | Sets viewport size. |
| `browser_wait_for` | Implemented | Waits for text, text disappearance, or a timeout. Prefer `time_seconds`; legacy `time` is also accepted and is interpreted as seconds. Values over 60 seconds return a structured error to catch millisecond/second mix-ups. |
| `browser_console_messages` | Implemented with difference | Returns tracked console messages. Optional `filename` writes the structured payload as JSON. |
| `browser_network_requests` | Implemented with difference | Returns tracked request summaries. Optional `filename` writes the structured payload as JSON. |
| `browser_network_request` | Implemented with difference | Returns one tracked request by index. Optional `filename` writes the structured payload as JSON. |
| `browser_tabs` | Implemented | Supports basic tab list/select/new/close actions. |
| `browser_take_screenshot` | Implemented with difference | Returns base64 image data in the structured result (`base64_png` for png, `base64_jpeg` for jpeg). Supports Node-style `type=png|jpeg`, `fullPage`, and `filename`, plus legacy `path` and `full_page`. Conflicting aliases return structured errors. Relative output paths resolve under `--output-dir`. When no path/filename is provided, Python creates a Node-style `page-{timestamp}.{png|jpeg}` file only if `--output-dir` or `PLAYWRIGHT_MCP_OUTPUT_DIR` is configured. Element/target screenshots and Node image response content are not implemented. |
| `browser_close` | Implemented | Closes context/browser/playwright process. |

Explicit relative output filenames are resolved under `--output-dir` or `PLAYWRIGHT_MCP_OUTPUT_DIR` for `browser_console_messages`, `browser_network_requests`, `browser_network_request`, `browser_snapshot`, `browser_evaluate`, and `browser_take_screenshot`. Absolute filenames keep their original absolute location. Observability, snapshot, and evaluate tools do not create automatic files when `filename` is omitted. Screenshot creates a Node-style `page-{timestamp}.{png|jpeg}` file only when an output directory is configured; it still does not implement Node's image-result response behavior.

## Node Oracle Differences

The Node implementation is a thin wrapper around `playwright-core/lib/coreBundle` (`tools.decorateMCPCommand` and `tools.createConnection`). Python cannot reuse that internal Node bundle, so this package directly implements a smaller MCP surface using Python Playwright.

Major known gaps:

- No accessibility snapshot parity. Node `browser_snapshot` is backed by `page.ariaSnapshot({ mode: "ai" })` / locator `ariaSnapshot` and supports `target`, `depth`, and `boxes`. Python `browser_snapshot` returns a text summary, not Playwright MCP's rich ARIA snapshot, and only supports `filename` output-file semantics.
- `browser_evaluate` is page-level only. Node coreBundle accepts `function`, optional `target`/`element`, and `filename`, evaluates either `page.evaluate(...)` or `locator.evaluate(...)`, then routes results through its response/file layer. Python accepts legacy `expression` and Node-style `function`, preserves its structured `ok`/`result` payload, and implements only page-level `filename` JSON output.
- `browser_run_code_unsafe` is intentionally not implemented.
- No storage, cookie, PDF, devtools, vision, route, tracing, video, or testing assertion tools yet.
- No config-file loader or environment-variable matrix matching the Node README. `--output-mode` and `PLAYWRIGHT_MCP_OUTPUT_MODE` are intentionally not implemented because current Node coreBundle inspection did not show response-layer handling that should be mirrored here.
- Response payloads preserve Python's structured `ok`/`error` dictionaries rather than matching Node response content arrays exactly.
- HTTP mode is Streamable HTTP via Python MCP SDK, not the Node oracle SSE transport.
- Session state is process-local. HTTP mode currently shares the same process-level browser manager and is not designed for independent per-client isolation.

Intentional non-goals for this deployment candidate:

- `browser_run_code_unsafe`.
- Accessibility snapshot parity, including `browser_snapshot` `target`, `depth`, and `boxes`.
- `browser_evaluate` `target`/`element` locator evaluation.
- Screenshot element/target semantics and Node image response content arrays.
- Full network headers/body parity.
- Cookie, localStorage, sessionStorage, storage-state, route/offline/network-state, PDF, vision/mouse-coordinate, tracing/video/devtools, and verification/locator-generation optional capability groups.
- Full CLI/config parity for caps, config files, proxy, CDP/remote endpoint, storage state, allowed/blocked origins, and related Node-only deployment options.

## Troubleshooting

- `python -m playwright_mcp --help`: verifies the package can be imported and the CLI entrypoint works.
- `No module named playwright_mcp`: run from the package/source directory, set MCP `cwd`, or install with `python -m pip install .`.
- Missing Playwright package: run `python -m pip install playwright`.
- Missing browser executable: run `python -m playwright install chromium`.
- Windows `cwd` issues: use a full path such as `D:\\src\\MCP\\playwright-mcp-main\\playwright-mcp-main` in your MCP client config.
- Headed launch issues: add `--headless` on servers or non-interactive desktops.
- Persistent profile locked: add `--isolated` or use a different `--user-data-dir`.

## Development Validation

From the repository root:

```powershell
python -m playwright_mcp --help
python -B -m unittest discover -s tests_python
python scripts\smoke_python_package.py
```

The browser launch portion of the smoke script is skipped when Python Playwright or Chromium is not installed.

