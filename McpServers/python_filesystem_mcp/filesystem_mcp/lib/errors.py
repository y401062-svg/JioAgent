from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    ACCESS_DENIED = "ACCESS_DENIED"
    NOT_FOUND = "NOT_FOUND"
    NOT_FILE = "NOT_FILE"
    NOT_DIRECTORY = "NOT_DIRECTORY"
    TOO_LARGE = "TOO_LARGE"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    INVALID_PATTERN = "INVALID_PATTERN"
    INVALID_INPUT = "INVALID_INPUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SYMLINK_NOT_ALLOWED = "SYMLINK_NOT_ALLOWED"
    UNKNOWN = "UNKNOWN"


class FilesystemMcpError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.path = path
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"code": self.code.value, "message": self.message}
        if self.path:
            result["path"] = self.path
        suggestion = get_suggestion(self.code)
        if suggestion:
            result["suggestion"] = suggestion
        return result


SUGGESTIONS = {
    ErrorCode.ACCESS_DENIED: "Run roots to list allowed directories.",
    ErrorCode.NOT_FOUND: "Run ls or find to verify the path.",
    ErrorCode.NOT_FILE: "Target is a directory, not a file.",
    ErrorCode.NOT_DIRECTORY: "Target is a file, not a directory.",
    ErrorCode.TOO_LARGE: "Use head/tail or line ranges to read partially.",
    ErrorCode.TIMEOUT: "Reduce scope, depth, or maxResults.",
    ErrorCode.INVALID_PATTERN: "Check syntax and escape special characters.",
    ErrorCode.PERMISSION_DENIED: "Check OS file permissions.",
    ErrorCode.SYMLINK_NOT_ALLOWED: "Symlink escapes allowed directories.",
}


def get_suggestion(code: ErrorCode) -> str | None:
    return SUGGESTIONS.get(code)


def classify_os_error(error: OSError) -> ErrorCode:
    if isinstance(error, FileNotFoundError):
        return ErrorCode.NOT_FOUND
    if isinstance(error, PermissionError):
        return ErrorCode.PERMISSION_DENIED
    if isinstance(error, IsADirectoryError):
        return ErrorCode.NOT_FILE
    if isinstance(error, NotADirectoryError):
        return ErrorCode.NOT_DIRECTORY
    return ErrorCode.UNKNOWN


def error_result(error: Exception, path: str | None = None) -> dict[str, Any]:
    if isinstance(error, FilesystemMcpError):
        return error.to_dict()
    if isinstance(error, OSError):
        code = classify_os_error(error)
        return FilesystemMcpError(code, str(error), path).to_dict()
    return FilesystemMcpError(ErrorCode.UNKNOWN, str(error), path).to_dict()
