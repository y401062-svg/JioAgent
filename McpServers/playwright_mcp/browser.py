from __future__ import annotations

import asyncio
import base64
import mimetypes
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote_to_bytes

from .lib.errors import ToolError
from .lib.state import BrowserConfig, PageSummary


_STALE_BROWSER_ERROR_HINT = (
    "The browser/page appears to have closed. Internal browser state was reset; retry the operation."
)
_PLAYWRIGHT_OPERATION_HINT = (
    "Check whether the target page crashed, navigation timed out, or the browser process was killed."
)
_STALE_ERROR_PATTERNS = (
    "target page, context or browser has been closed",
    "browser has been closed",
    "context has been closed",
    "page has been closed",
    "browser is closed",
    "context is closed",
    "page is closed",
    "connection closed",
    "browser disconnected",
    "browser has disconnected",
    "browser process",
    "target closed",
    "page crashed",
    "crash",
)
_OPERATION_TIMEOUT_SECONDS = 25.0
_DATA_URL_NAVIGATION_TIMEOUT_SECONDS = 10.0


class BrowserManager:
    def __init__(self, config: BrowserConfig):
        self.config = config
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._dialog: Any = None
        self._file_chooser: Any = None
        self._navigation_id = 0
        self._console_messages: list[dict[str, Any]] = []
        self._network_requests: list[dict[str, Any]] = []
        self._network_request_indexes: dict[int, dict[str, Any]] = {}
        self._operation_lock = asyncio.Lock()

    async def run_exclusive(self, awaitable: Any) -> Any:
        async with self._operation_lock:
            try:
                return await asyncio.wait_for(awaitable, timeout=_OPERATION_TIMEOUT_SECONDS)
            except asyncio.TimeoutError as exc:
                self._reset_page_state()
                raise ToolError(
                    "browser_operation_timeout",
                    f"Browser operation did not complete within {_OPERATION_TIMEOUT_SECONDS:g} seconds.",
                    "The in-flight browser operation was cancelled and page state was reset; retry or close the browser.",
                ) from exc

    async def ensure_page(self) -> Any:
        self._discard_stale_handles()
        if self._page and not self._page.is_closed():
            return self._page
        await self._ensure_context()
        self._page = await self._context.new_page()
        self._apply_timeouts(self._page)
        self._wire_page_events(self._page)
        return self._page

    async def close(self) -> None:
        errors: list[str] = []
        for attr in ("_context", "_browser"):
            obj = getattr(self, attr)
            if obj:
                try:
                    await obj.close()
                except Exception as exc:  # pragma: no cover - best-effort cleanup
                    errors.append(str(exc))
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as exc:  # pragma: no cover - best-effort cleanup
                errors.append(str(exc))
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._dialog = None
        self._file_chooser = None
        if errors:
            raise ToolError("browser_close_failed", "; ".join(errors))

    async def navigate(self, url: str) -> PageSummary:
        page = await self.ensure_page()
        try:
            self._begin_navigation()
            if self._is_html_data_url(url):
                html = self._html_from_data_url(url)
                await asyncio.wait_for(
                    page.set_content(
                        html,
                        wait_until="domcontentloaded",
                        timeout=min(self.config.navigation_timeout_ms, int(_DATA_URL_NAVIGATION_TIMEOUT_SECONDS * 1000)),
                    ),
                    timeout=_DATA_URL_NAVIGATION_TIMEOUT_SECONDS,
                )
            else:
                await page.goto(url, wait_until="domcontentloaded", timeout=self.config.navigation_timeout_ms)
            return await self.summary()
        except ToolError:
            raise
        except asyncio.TimeoutError as exc:
            raise self._tool_error(exc, "navigation_failed")
        except Exception as exc:
            raise self._tool_error(exc, "navigation_failed")

    async def navigate_back(self) -> PageSummary:
        page = await self.ensure_page()
        try:
            self._begin_navigation()
            await page.go_back(wait_until="domcontentloaded", timeout=self.config.navigation_timeout_ms)
            return await self.summary()
        except Exception as exc:
            raise self._tool_error(exc, "navigation_back_failed")

    async def summary(self) -> PageSummary:
        page = await self.ensure_page()
        try:
            title = await page.title()
            url = page.url
            text = await page.locator("body").inner_text(timeout=self.config.action_timeout_ms)
            return PageSummary(url=url, title=title, text=self._trim(text))
        except Exception as exc:
            raise self._tool_error(exc, "snapshot_failed")

    async def click(self, selector: str) -> PageSummary:
        try:
            await (await self._locator(selector)).click(timeout=self.config.action_timeout_ms)
            return await self.summary()
        except Exception as exc:
            raise self._tool_error(exc, "click_failed")

    async def hover(self, selector: str) -> PageSummary:
        try:
            await (await self._locator(selector)).hover(timeout=self.config.action_timeout_ms)
            return await self.summary()
        except Exception as exc:
            raise self._tool_error(exc, "hover_failed")

    async def select_option(self, selector: str, values: list[str]) -> PageSummary:
        try:
            await (await self._locator(selector)).select_option(values, timeout=self.config.action_timeout_ms)
            return await self.summary()
        except Exception as exc:
            raise self._tool_error(exc, "select_option_failed")

    async def fill_form(self, fields: list[dict[str, Any]]) -> PageSummary:
        try:
            for field in fields:
                selector = self._field_selector(field)
                value = field.get("value", "")
                field_type = str(field.get("type", "")).lower()
                locator = await self._locator(selector)
                tag_name = await self._locator_tag_name(locator)
                if field_type in ("checkbox", "radio") and isinstance(value, bool):
                    if value:
                        await locator.check(timeout=self.config.action_timeout_ms)
                    else:
                        await locator.uncheck(timeout=self.config.action_timeout_ms)
                elif field_type in ("select", "combobox") or tag_name == "select":
                    option_values = value if isinstance(value, list) else [str(value)]
                    await locator.select_option(option_values, timeout=self.config.action_timeout_ms)
                else:
                    await locator.fill(str(value), timeout=self.config.action_timeout_ms)
            return await self.summary()
        except ToolError:
            raise
        except Exception as exc:
            raise self._tool_error(exc, "fill_form_failed")

    async def file_upload(self, paths: list[str] | None = None) -> PageSummary:
        page = await self.ensure_page()
        try:
            upload_paths = [str(Path(path).expanduser()) for path in paths or []]
            if self._file_chooser:
                chooser = self._file_chooser
                self._file_chooser = None
                await chooser.set_files(upload_paths)
            else:
                await (await self._locator('input[type="file"]')).set_input_files(
                    upload_paths, timeout=self.config.action_timeout_ms
                )
            return await self.summary()
        except Exception as exc:
            raise self._tool_error(exc, "file_upload_failed")

    async def handle_dialog(self, accept: bool, prompt_text: str | None = None) -> PageSummary:
        await self.ensure_page()
        try:
            if not self._dialog:
                raise ToolError("missing_dialog", "No dialog is currently pending")
            dialog = self._dialog
            self._dialog = None
            if accept:
                await dialog.accept(prompt_text)
            else:
                await dialog.dismiss()
            return await self.summary()
        except ToolError:
            raise
        except Exception as exc:
            raise self._tool_error(exc, "handle_dialog_failed")

    async def drag(self, start_selector: str, end_selector: str) -> PageSummary:
        try:
            await (await self._locator(start_selector)).drag_to(
                await self._locator(end_selector), timeout=self.config.action_timeout_ms
            )
            return await self.summary()
        except Exception as exc:
            raise self._tool_error(exc, "drag_failed")

    async def drop(
        self, selector: str, paths: list[str] | None = None, data: dict[str, str] | None = None
    ) -> PageSummary:
        page = await self.ensure_page()
        try:
            if not paths and not data:
                raise ToolError("missing_drop_payload", 'At least one of "paths" or "data" is required')
            file_payloads = [self._drop_file_payload(path) for path in paths or []]
            data_transfer = await page.evaluate_handle(
                """payload => {
                    const dt = new DataTransfer();
                    for (const [type, value] of Object.entries(payload.data || {}))
                        dt.setData(type, value);
                    for (const file of payload.files || [])
                        dt.items.add(new File([new Uint8Array(file.bytes)], file.name, { type: file.type }));
                    return dt;
                }""",
                {"data": data or {}, "files": file_payloads},
            )
            locator = await self._locator(selector)
            event_init = {"dataTransfer": data_transfer}
            await locator.dispatch_event("dragenter", event_init, timeout=self.config.action_timeout_ms)
            await locator.dispatch_event("dragover", event_init, timeout=self.config.action_timeout_ms)
            await locator.dispatch_event("drop", event_init, timeout=self.config.action_timeout_ms)
            return await self.summary()
        except ToolError:
            raise
        except Exception as exc:
            raise self._tool_error(exc, "drop_failed")

    async def type_text(self, selector: str, text: str, submit: bool = False) -> PageSummary:
        try:
            locator = await self._locator(selector)
            await locator.fill(text, timeout=self.config.action_timeout_ms)
            if submit:
                await locator.press("Enter", timeout=self.config.action_timeout_ms)
            return await self.summary()
        except Exception as exc:
            raise self._tool_error(exc, "type_failed")

    async def press_key(self, key: str, selector: str | None = None) -> PageSummary:
        page = await self.ensure_page()
        try:
            if selector:
                await (await self._locator(selector)).press(key, timeout=self.config.action_timeout_ms)
            else:
                await page.keyboard.press(key)
            return await self.summary()
        except Exception as exc:
            raise self._tool_error(exc, "press_key_failed")

    async def evaluate(self, expression: str) -> Any:
        page = await self.ensure_page()
        try:
            return await page.evaluate(expression)
        except Exception as exc:
            raise self._tool_error(exc, "evaluate_failed")

    async def resize(self, width: int, height: int) -> PageSummary:
        page = await self.ensure_page()
        try:
            await page.set_viewport_size({"width": width, "height": height})
            return await self.summary()
        except Exception as exc:
            raise self._tool_error(exc, "resize_failed")

    async def wait_for(
        self, time: float | None = None, text: str | None = None, text_gone: str | None = None
    ) -> PageSummary:
        page = await self.ensure_page()
        try:
            if time is not None:
                await page.wait_for_timeout(time * 1000)
            if text:
                await page.get_by_text(text).wait_for(state="visible", timeout=self.config.action_timeout_ms)
            if text_gone:
                await page.get_by_text(text_gone).wait_for(state="hidden", timeout=self.config.action_timeout_ms)
            return await self.summary()
        except Exception as exc:
            raise self._tool_error(exc, "wait_for_failed")

    async def tabs(self, action: str, index: int | None = None, url: str | None = None) -> dict[str, Any]:
        await self._ensure_context()
        try:
            normalized = action.lower()
            if normalized in ("new", "create"):
                page = await self._context.new_page()
                self._apply_timeouts(page)
                self._wire_page_events(page)
                self._page = page
                if url:
                    self._begin_navigation()
                    await page.goto(url, wait_until="domcontentloaded", timeout=self.config.navigation_timeout_ms)
            elif normalized == "select":
                self._page = self._context.pages[self._require_tab_index(index)]
            elif normalized == "close":
                page = self._context.pages[self._require_tab_index(index)] if index is not None else await self.ensure_page()
                await page.close()
                pages = [candidate for candidate in self._context.pages if not candidate.is_closed()]
                self._page = pages[min(index or 0, len(pages) - 1)] if pages else None
            elif normalized != "list":
                raise ToolError("invalid_tab_action", f"Unsupported tab action: {action}")
            return await self._tabs_state()
        except ToolError:
            raise
        except Exception as exc:
            raise self._tool_error(exc, "tabs_failed")

    async def console_messages(self, level: str = "info", all: bool = False) -> dict[str, Any]:
        await self.ensure_page()
        try:
            levels = {"debug": 0, "log": 1, "info": 1, "warning": 2, "error": 3}
            minimum = levels.get(level, levels["info"])
            messages = [
                message
                for message in self._console_messages
                if (all or message.get("navigation_id") == self._navigation_id)
                and levels.get(str(message.get("level")), levels["info"]) >= minimum
            ]
            return {"messages": [self._without_internal_keys(message) for message in messages]}
        except Exception as exc:
            raise self._tool_error(exc, "console_messages_failed")

    async def network_requests(self, static: bool = False, filter: str | None = None) -> dict[str, Any]:
        await self.ensure_page()
        try:
            url_pattern = re.compile(filter) if filter else None
            requests = [
                request
                for request in self._network_requests
                if (static or not self._is_successful_static_request(request))
                and (url_pattern is None or url_pattern.search(str(request.get("url"))))
            ]
            return {"requests": [self._without_internal_keys(request) for request in requests]}
        except re.error as exc:
            raise ToolError("invalid_network_filter", str(exc))
        except Exception as exc:
            raise self._tool_error(exc, "network_requests_failed")

    async def network_request(self, index: int, part: str | None = None) -> dict[str, Any]:
        await self.ensure_page()
        try:
            if index < 1 or index > len(self._network_requests):
                raise ToolError("invalid_network_request_index", f"Network request index out of range: {index}")
            request = self._without_internal_keys(self._network_requests[index - 1])
            if part:
                if part not in self._network_request_parts():
                    raise ToolError("invalid_network_request_part", f"Unknown network request part: {part}")
                return {"request": {part: request[part]}}
            return {"request": request}
        except ToolError:
            raise
        except Exception as exc:
            raise self._tool_error(exc, "network_request_failed")

    async def screenshot(
        self, path: str | None = None, full_page: bool = False, image_type: str = "png"
    ) -> dict[str, Any]:
        import base64

        page = await self.ensure_page()
        try:
            kwargs: dict[str, Any] = {"full_page": full_page, "type": image_type}
            output: Path | None = None
            if path:
                output = self._resolve_output_path(path)
                output.parent.mkdir(parents=True, exist_ok=True)
                kwargs["path"] = str(output)
            data = await page.screenshot(**kwargs)
            result = {
                "url": page.url,
                "path": str(output) if output else None,
                "image_type": image_type,
            }
            encoded = base64.b64encode(data).decode("ascii")
            if image_type == "jpeg":
                result["base64_jpeg"] = encoded
            else:
                result["base64_png"] = encoded
            return result
        except Exception as exc:
            raise self._tool_error(exc, "screenshot_failed")

    async def _ensure_context(self) -> None:
        self._discard_stale_handles()
        if self._context:
            return
        await self._start_playwright()
        browser_launcher = self._browser_launcher()
        launch_options = self._launch_options()
        context_options = self._context_options()
        try:
            if self.config.user_data_dir and not self.config.isolated:
                self._context = await browser_launcher.launch_persistent_context(
                    str(self.config.user_data_dir), **launch_options, **context_options
                )
                for page in self._context.pages:
                    self._apply_timeouts(page)
                    self._wire_page_events(page)
            else:
                self._browser = await browser_launcher.launch(**launch_options)
                self._wire_browser_events(self._browser)
                self._context = await self._browser.new_context(**context_options)
            self._wire_context_events(self._context)
        except Exception as exc:
            raise self._tool_error(exc, "browser_launch_failed")

    async def _start_playwright(self) -> None:
        if self._playwright:
            return
        try:
            from playwright.async_api import async_playwright
        except ModuleNotFoundError as exc:
            raise ToolError(
                "playwright_not_installed",
                "Python package 'playwright' is not installed. Run: python -m pip install playwright",
            ) from exc
        self._playwright = await async_playwright().start()

    def _browser_launcher(self) -> Any:
        browser = self.config.browser_type.lower()
        if browser in ("chrome", "msedge"):
            return self._playwright.chromium
        if browser not in ("chromium", "firefox", "webkit"):
            raise ToolError("unsupported_browser", f"Unsupported browser type: {self.config.browser_type}")
        return getattr(self._playwright, browser)

    def _launch_options(self) -> dict[str, Any]:
        browser = self.config.browser_type.lower()
        options: dict[str, Any] = {"headless": self.config.headless}
        if browser in ("chrome", "msedge"):
            options["channel"] = browser
        if self.config.no_sandbox:
            options["args"] = ["--no-sandbox"]
        return options

    def _context_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {}
        if self.config.viewport:
            width, height = self.config.viewport
            options["viewport"] = {"width": width, "height": height}
        return options

    def _apply_timeouts(self, page: Any) -> None:
        page.set_default_timeout(self.config.action_timeout_ms)
        page.set_default_navigation_timeout(self.config.navigation_timeout_ms)

    def _wire_page_events(self, page: Any) -> None:
        page.on("close", lambda *_, page=page: self._reset_page_state(page))
        page.on("crash", lambda *_, page=page: self._reset_page_state(page))
        page.on("dialog", self._remember_dialog)
        page.on("filechooser", self._remember_file_chooser)
        page.on("console", self._remember_console_message)
        page.on("request", self._remember_network_request)
        page.on("response", self._remember_network_response)
        page.on("requestfailed", self._remember_network_failure)

    def _wire_browser_events(self, browser: Any) -> None:
        try:
            browser.on("disconnected", lambda *_: self._reset_browser_state())
        except Exception:
            pass

    def _wire_context_events(self, context: Any) -> None:
        try:
            context.on("close", lambda *_: self._reset_context_state())
        except Exception:
            pass

    def _remember_dialog(self, dialog: Any) -> None:
        self._dialog = dialog

    def _remember_file_chooser(self, file_chooser: Any) -> None:
        self._file_chooser = file_chooser

    def _remember_console_message(self, message: Any) -> None:
        location = getattr(message, "location", None)
        self._console_messages.append(
            {
                "level": self._console_level(getattr(message, "type", "info")),
                "text": getattr(message, "text", ""),
                "location": location if isinstance(location, dict) else None,
                "navigation_id": self._navigation_id,
            }
        )

    def _remember_network_request(self, request: Any) -> None:
        entry = {
            "index": len(self._network_requests) + 1,
            "url": getattr(request, "url", ""),
            "method": getattr(request, "method", ""),
            "resourceType": getattr(request, "resource_type", None),
            "status": None,
            "failed": False,
            "failure": None,
        }
        self._network_requests.append(entry)
        self._network_request_indexes[id(request)] = entry

    def _remember_network_response(self, response: Any) -> None:
        request = getattr(response, "request", None)
        entry = self._network_request_indexes.get(id(request))
        if entry is not None:
            entry["status"] = getattr(response, "status", None)

    def _remember_network_failure(self, request: Any) -> None:
        entry = self._network_request_indexes.get(id(request))
        if entry is not None:
            entry["failed"] = True
            failure = getattr(request, "failure", None)
            entry["failure"] = failure if isinstance(failure, str) else None

    def _begin_navigation(self) -> None:
        self._navigation_id += 1
        self._network_requests.clear()
        self._network_request_indexes.clear()

    def _discard_stale_handles(self) -> None:
        if self._browser and not self._is_browser_connected(self._browser):
            self._reset_browser_state()
            return
        if self._context and not self._is_context_usable(self._context):
            self._reset_context_state()
            return
        if self._page and self._is_page_closed(self._page):
            self._reset_page_state()

    def _reset_browser_state(self) -> None:
        self._browser = None
        self._reset_context_state()

    def _reset_context_state(self) -> None:
        self._context = None
        self._reset_page_state()

    def _reset_page_state(self, page: Any | None = None) -> None:
        if page is not None and page is not self._page:
            return
        self._page = None
        self._dialog = None
        self._file_chooser = None

    @staticmethod
    def _is_browser_connected(browser: Any) -> bool:
        is_connected = getattr(browser, "is_connected", None)
        if not callable(is_connected):
            return True
        try:
            return bool(is_connected())
        except Exception:
            return False

    @staticmethod
    def _is_context_usable(context: Any) -> bool:
        try:
            pages = getattr(context, "pages", [])
            for page in pages:
                is_closed = getattr(page, "is_closed", None)
                if callable(is_closed):
                    is_closed()
            return True
        except Exception:
            return False

    @staticmethod
    def _is_page_closed(page: Any) -> bool:
        is_closed = getattr(page, "is_closed", None)
        if not callable(is_closed):
            return False
        try:
            return bool(is_closed())
        except Exception:
            return True

    async def _locator(self, selector: str) -> Any:
        page = await self.ensure_page()
        if self.config.frame_selector:
            return page.frame_locator(self.config.frame_selector).locator(selector)
        return page.locator(selector)

    async def _locator_tag_name(self, locator: Any) -> str:
        evaluate = getattr(locator, "evaluate", None)
        if not callable(evaluate):
            return ""
        try:
            tag_name = await evaluate("element => element.tagName.toLowerCase()")
        except Exception:
            return ""
        return str(tag_name).lower()

    @staticmethod
    def _field_selector(field: dict[str, Any]) -> str:
        for key in ("target", "selector", "ref", "name"):
            value = field.get(key)
            if value:
                return str(value)
        raise ToolError("missing_field_target", "Form field is missing target, selector, ref, or name")

    @staticmethod
    def _drop_file_payload(path: str) -> dict[str, Any]:
        file_path = Path(path).expanduser()
        return {
            "name": file_path.name,
            "type": mimetypes.guess_type(file_path.name)[0] or "application/octet-stream",
            "bytes": list(file_path.read_bytes()),
        }

    def _resolve_output_path(self, path: str) -> Path:
        output = Path(path).expanduser()
        if self.config.output_dir and not output.is_absolute():
            output = self.config.output_dir.expanduser() / output
        return output

    def _require_tab_index(self, index: int | None) -> int:
        if index is None:
            raise ToolError("missing_tab_index", "Tab index is required for this action")
        pages = self._context.pages
        if index < 0 or index >= len(pages):
            raise ToolError("invalid_tab_index", f"Tab index out of range: {index}")
        return index

    async def _tabs_state(self) -> dict[str, Any]:
        pages = self._context.pages if self._context else []
        current = await self.ensure_page()
        tabs = []
        for index, page in enumerate(pages):
            if page.is_closed():
                continue
            tabs.append(
                {
                    "index": index,
                    "url": page.url,
                    "title": await page.title(),
                    "current": page == current,
                }
            )
        return {"tabs": tabs}

    @staticmethod
    def _console_level(level: str) -> str:
        if level == "warning":
            return "warning"
        if level in ("error", "debug", "info"):
            return level
        return "info"

    @staticmethod
    def _is_successful_static_request(request: dict[str, Any]) -> bool:
        status = request.get("status")
        resource_type = request.get("resourceType")
        return isinstance(status, int) and 200 <= status < 400 and resource_type in {
            "image",
            "stylesheet",
            "font",
            "script",
            "media",
        }

    @staticmethod
    def _network_request_parts() -> set[str]:
        return {"index", "url", "method", "resourceType", "status", "failed", "failure"}

    @staticmethod
    def _without_internal_keys(value: dict[str, Any]) -> dict[str, Any]:
        return {key: item for key, item in value.items() if key != "navigation_id"}

    @staticmethod
    def _trim(text: str, limit: int = 12000) -> str:
        compact = "\n".join(line.rstrip() for line in text.splitlines() if line.strip())
        return compact[:limit] + ("\n...[truncated]" if len(compact) > limit else "")

    @staticmethod
    def _is_html_data_url(url: str) -> bool:
        return url.lower().startswith("data:text/html")

    @staticmethod
    def _html_from_data_url(url: str) -> str:
        if "," not in url:
            raise ToolError(
                "invalid_data_url",
                "data:text/html URL is missing a comma separator.",
                "Use data:text/html,<html>...</html> or a percent-encoded HTML payload.",
            )
        metadata, payload = url[5:].split(",", 1)
        raw = unquote_to_bytes(payload)
        if ";base64" in metadata.lower():
            try:
                raw = base64.b64decode(raw, validate=True)
            except Exception as exc:
                raise ToolError(
                    "invalid_data_url",
                    "data:text/html base64 payload could not be decoded.",
                    "Use a valid base64 payload after data:text/html;base64,.",
                ) from exc
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1")

    def _tool_error(self, exc: Exception, fallback_code: str) -> ToolError:
        name = exc.__class__.__name__.lower()
        message = str(exc)
        if self._is_stale_error(exc):
            self._reset_browser_state()
            return ToolError("browser_closed", message, _STALE_BROWSER_ERROR_HINT)
        if "timeout" in name:
            code = "playwright_timeout"
        elif "error" in name:
            code = fallback_code
        else:
            code = fallback_code
        return ToolError(code, message, _PLAYWRIGHT_OPERATION_HINT)

    @staticmethod
    def _is_stale_error(exc: Exception) -> bool:
        text = f"{exc.__class__.__name__}: {exc}".lower()
        return any(pattern in text for pattern in _STALE_ERROR_PATTERNS)
