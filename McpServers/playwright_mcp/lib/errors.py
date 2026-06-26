from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolError(Exception):
    code: str
    message: str
    hint: str | None = None

    def to_result(self) -> dict[str, Any]:
        error = {"code": self.code, "message": self.message}
        if self.hint:
            error["hint"] = self.hint
        return {"ok": False, "error": error}


def ok_result(**payload: Any) -> dict[str, Any]:
    return {"ok": True, **payload}


def error_result(code: str, message: str, hint: str | None = None) -> dict[str, Any]:
    return ToolError(code, message, hint).to_result()
