from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class BrowserConfig:
    browser_type: str = "chromium"
    headless: bool = False
    isolated: bool = False
    user_data_dir: Path | None = None
    viewport: tuple[int, int] | None = None
    host: str = "127.0.0.1"
    port: int | None = None
    action_timeout_ms: int = 5000
    navigation_timeout_ms: int = 60000
    no_sandbox: bool = False
    output_dir: Path | None = None
    frame_selector: str | None = None


@dataclass
class PageSummary:
    url: str
    title: str
    text: str
