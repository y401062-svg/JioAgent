from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .browser import BrowserManager
from .lib.errors import ToolError, error_result, ok_result


_UNEXPECTED_ERROR_HINT = "The MCP server caught an unexpected tool error; retry or inspect server logs for details."
_MAX_WAIT_SECONDS = 60.0


def register_tools(server: FastMCP, browser: BrowserManager) -> None:
    @server.tool()
    async def browser_navigate(url: str) -> dict[str, Any]:
        """Navigate the browser page to a URL."""
        return await _with_summary(browser.navigate(url), browser)

    @server.tool()
    async def browser_navigate_back() -> dict[str, Any]:
        """Go back to the previous page in the browser history."""
        return await _with_summary(browser.navigate_back(), browser)

    @server.tool()
    async def browser_snapshot(filename: str | None = None) -> dict[str, Any]:
        """Return a text snapshot of the current page."""
        try:
            summary = await _run_browser_operation(browser, browser.summary())
            data = {"url": summary.url, "title": summary.title, "text": summary.text}
            return ok_result(**_with_optional_output_file(data, filename, browser.config.output_dir))
        except ToolError as exc:
            return exc.to_result()
        except Exception as exc:  # pragma: no cover - defensive MCP boundary
            return error_result("unexpected_error", str(exc), _UNEXPECTED_ERROR_HINT)

    @server.tool()
    async def browser_click(selector: str) -> dict[str, Any]:
        """Click an element selected by a Playwright selector."""
        return await _with_summary(browser.click(selector), browser)

    @server.tool()
    async def browser_hover(target: str, element: str | None = None) -> dict[str, Any]:
        """Hover over an element selected by a Playwright selector."""
        return await _with_summary(browser.hover(target), browser)

    @server.tool()
    async def browser_select_option(target: str, values: list[str], element: str | None = None) -> dict[str, Any]:
        """Select option values in a dropdown selected by a Playwright selector."""
        return await _with_summary(browser.select_option(target, values), browser)

    @server.tool()
    async def browser_fill_form(fields: list[dict[str, Any]]) -> dict[str, Any]:
        """Fill multiple form fields."""
        return await _with_summary(browser.fill_form(fields), browser)

    @server.tool()
    async def browser_file_upload(paths: list[str] | None = None) -> dict[str, Any]:
        """Upload one or more files using a pending file chooser or file input."""
        return await _with_summary(browser.file_upload(paths), browser)

    @server.tool()
    async def browser_handle_dialog(accept: bool, promptText: str | None = None) -> dict[str, Any]:
        """Accept or dismiss the latest pending browser dialog."""
        return await _with_summary(browser.handle_dialog(accept, promptText), browser)

    @server.tool()
    async def browser_drag(
        startTarget: str,
        endTarget: str,
        startElement: str | None = None,
        endElement: str | None = None,
    ) -> dict[str, Any]:
        """Perform drag and drop between two elements selected by Playwright selectors."""
        return await _with_summary(browser.drag(startTarget, endTarget), browser)

    @server.tool()
    async def browser_drop(
        target: str,
        paths: list[str] | None = None,
        data: dict[str, str] | None = None,
        element: str | None = None,
    ) -> dict[str, Any]:
        """Drop files or MIME-typed data onto an element."""
        return await _with_summary(browser.drop(target, paths=paths, data=data), browser)

    @server.tool()
    async def browser_type(selector: str, text: str, submit: bool = False) -> dict[str, Any]:
        """Fill text into an element selected by a Playwright selector."""
        return await _with_summary(browser.type_text(selector, text, submit), browser)

    @server.tool()
    async def browser_press_key(key: str, selector: str | None = None) -> dict[str, Any]:
        """Press a keyboard key, optionally scoped to a selector."""
        return await _with_summary(browser.press_key(key, selector), browser)

    @server.tool()
    async def browser_evaluate(
        expression: str | None = None,
        filename: str | None = None,
        function: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate JavaScript in the current page and return the result."""
        try:
            expression = _evaluate_expression(expression, function)
            value = await _run_browser_operation(browser, browser.evaluate(expression))
            data = {"result": value}
            return ok_result(**_with_optional_output_file(data, filename, browser.config.output_dir))
        except ToolError as exc:
            return exc.to_result()
        except Exception as exc:  # pragma: no cover - defensive MCP boundary
            return error_result("unexpected_error", str(exc), _UNEXPECTED_ERROR_HINT)

    @server.tool()
    async def browser_resize(width: int, height: int) -> dict[str, Any]:
        """Resize the current page viewport."""
        return await _with_summary(browser.resize(width, height), browser)

    @server.tool()
    async def browser_wait_for(
        time_seconds: float | None = None,
        time: float | None = None,
        text: str | None = None,
        textGone: str | None = None,
    ) -> dict[str, Any]:
        """Wait for text to appear, disappear, or for a time interval in seconds."""
        try:
            seconds = _wait_for_seconds(time_seconds=time_seconds, time=time)
            return await _with_summary(browser.wait_for(time=seconds, text=text, text_gone=textGone), browser)
        except ToolError as exc:
            return exc.to_result()
        except Exception as exc:  # pragma: no cover - defensive MCP boundary
            return error_result("unexpected_error", str(exc), _UNEXPECTED_ERROR_HINT)

    @server.tool()
    async def browser_console_messages(
        level: str = "info", all: bool = False, filename: str | None = None
    ) -> dict[str, Any]:
        """Return console messages captured from the current browser session."""
        try:
            data = await _run_browser_operation(browser, browser.console_messages(level=level, all=all))
            return ok_result(**_with_optional_output_file(data, filename, browser.config.output_dir))
        except ToolError as exc:
            return exc.to_result()
        except Exception as exc:  # pragma: no cover - defensive MCP boundary
            return error_result("unexpected_error", str(exc), _UNEXPECTED_ERROR_HINT)

    @server.tool()
    async def browser_network_requests(
        static: bool = False, filter: str | None = None, filename: str | None = None
    ) -> dict[str, Any]:
        """Return network requests captured since the last page navigation."""
        try:
            data = await _run_browser_operation(browser, browser.network_requests(static=static, filter=filter))
            return ok_result(**_with_optional_output_file(data, filename, browser.config.output_dir))
        except ToolError as exc:
            return exc.to_result()
        except Exception as exc:  # pragma: no cover - defensive MCP boundary
            return error_result("unexpected_error", str(exc), _UNEXPECTED_ERROR_HINT)

    @server.tool()
    async def browser_network_request(
        index: int, part: str | None = None, filename: str | None = None
    ) -> dict[str, Any]:
        """Return basic details for a captured network request by 1-based index."""
        try:
            data = await _run_browser_operation(browser, browser.network_request(index=index, part=part))
            return ok_result(**_with_optional_output_file(data, filename, browser.config.output_dir))
        except ToolError as exc:
            return exc.to_result()
        except Exception as exc:  # pragma: no cover - defensive MCP boundary
            return error_result("unexpected_error", str(exc), _UNEXPECTED_ERROR_HINT)

    @server.tool()
    async def browser_tabs(action: str, index: int | None = None, url: str | None = None) -> dict[str, Any]:
        """List, create, close, or select a browser tab."""
        try:
            data = await _run_browser_operation(browser, browser.tabs(action=action, index=index, url=url))
            return ok_result(**data)
        except ToolError as exc:
            return exc.to_result()
        except Exception as exc:  # pragma: no cover - defensive MCP boundary
            return error_result("unexpected_error", str(exc), _UNEXPECTED_ERROR_HINT)

    @server.tool()
    async def browser_take_screenshot(
        path: str | None = None,
        filename: str | None = None,
        full_page: bool | None = None,
        fullPage: bool | None = None,
        type: str = "png",
    ) -> dict[str, Any]:
        """Take a screenshot of the current page."""
        try:
            image_type = _screenshot_type(type)
            resolved_full_page = _screenshot_full_page(full_page, fullPage)
            screenshot_path = _screenshot_path(path, filename)
            if not screenshot_path and browser.config.output_dir:
                screenshot_path = _default_screenshot_filename(image_type)
            data = await _run_browser_operation(
                browser,
                browser.screenshot(path=screenshot_path, full_page=resolved_full_page, image_type=image_type),
            )
            return ok_result(**data)
        except ToolError as exc:
            return exc.to_result()
        except Exception as exc:  # pragma: no cover - defensive MCP boundary
            return error_result("unexpected_error", str(exc), _UNEXPECTED_ERROR_HINT)

    @server.tool()
    async def browser_close() -> dict[str, Any]:
        """Close the browser context and process."""
        try:
            await _run_browser_operation(browser, browser.close())
            return ok_result(message="Browser closed")
        except ToolError as exc:
            return exc.to_result()
        except Exception as exc:  # pragma: no cover - defensive MCP boundary
            return error_result("unexpected_error", str(exc), _UNEXPECTED_ERROR_HINT)


async def _with_summary(awaitable: Any, browser: BrowserManager | None = None) -> dict[str, Any]:
    try:
        summary = await _run_browser_operation(browser, awaitable)
        return ok_result(url=summary.url, title=summary.title, text=summary.text)
    except ToolError as exc:
        return exc.to_result()
    except Exception as exc:  # pragma: no cover - defensive MCP boundary
        return error_result("unexpected_error", str(exc), _UNEXPECTED_ERROR_HINT)


async def _run_browser_operation(browser: BrowserManager | None, awaitable: Any) -> Any:
    if browser is None:
        return await awaitable
    runner = getattr(browser, "run_exclusive", None)
    if callable(runner):
        return await runner(awaitable)
    return await awaitable


def _with_optional_output_file(
    payload: dict[str, Any], filename: str | None, output_dir: Path | None = None
) -> dict[str, Any]:
    if not filename:
        return payload
    output = Path(filename).expanduser()
    if output_dir and not output.is_absolute():
        output = output_dir.expanduser() / output
    if output.exists() and output.is_dir():
        raise ToolError("invalid_output_filename", f"Output filename points to a directory: {filename}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**payload, "output_file": str(output)}


def _evaluate_expression(expression: str | None, function: str | None) -> str:
    if expression and function and expression != function:
        raise ToolError(
            "ambiguous_evaluate_expression",
            'Use either legacy "expression" or Node-style "function", not both',
        )
    resolved = expression or function
    if not resolved:
        raise ToolError(
            "missing_evaluate_expression",
            'Use legacy "expression" or Node-style "function" to evaluate JavaScript',
        )
    return resolved


def _screenshot_path(path: str | None, filename: str | None) -> str | None:
    if path and filename and Path(path).expanduser() != Path(filename).expanduser():
        raise ToolError("ambiguous_screenshot_filename", 'Use either "filename" or legacy "path", not both')
    return filename or path


def _screenshot_type(image_type: str) -> str:
    if image_type not in {"png", "jpeg"}:
        raise ToolError("invalid_screenshot_type", 'Screenshot type must be "png" or "jpeg"')
    return image_type


def _screenshot_full_page(full_page: bool | None, fullPage: bool | None) -> bool:
    if full_page is not None and fullPage is not None and full_page != fullPage:
        raise ToolError("ambiguous_screenshot_full_page", 'Use either "fullPage" or "full_page", not both')
    return bool(fullPage if fullPage is not None else full_page)


def _wait_for_seconds(time_seconds: float | None, time: float | None) -> float | None:
    if time_seconds is not None and time is not None and time_seconds != time:
        raise ToolError(
            "ambiguous_wait_time",
            'Use either "time_seconds" or legacy "time", not both.',
            'Both values are seconds. For a 1 second wait, pass {"time_seconds": 1}.',
        )
    seconds = time_seconds if time_seconds is not None else time
    if seconds is None:
        return None
    if seconds < 0:
        raise ToolError(
            "invalid_wait_time",
            "Wait time must be zero or greater.",
            'browser_wait_for uses seconds. For 1000 ms, pass {"time_seconds": 1}.',
        )
    if seconds > _MAX_WAIT_SECONDS:
        raise ToolError(
            "wait_time_too_large",
            f"Wait time must be {_MAX_WAIT_SECONDS:g} seconds or less.",
            'browser_wait_for uses seconds, not milliseconds. For 1000 ms, pass {"time_seconds": 1}.',
        )
    return seconds


def _default_screenshot_filename(image_type: str = "png") -> str:
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z").replace(":", "-").replace(".", "-")
    return f"page-{timestamp}.{image_type}"
