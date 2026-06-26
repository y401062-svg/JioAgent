from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path

from .constants import SENSITIVE_FILE_ALLOWLIST, SENSITIVE_FILE_DENYLIST
from .errors import ErrorCode, FilesystemMcpError

IS_WINDOWS = os.name == "nt"
RESERVED_DEVICE_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}

_allowed_primary: list[Path] = []
_allowed_expanded: list[Path] = []


def _norm_string(path: Path) -> str:
    text = str(path.resolve(strict=False))
    return text.lower() if IS_WINDOWS else text


def _dedupe(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = _norm_string(path)
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def normalize_path(value: str) -> Path:
    expanded = os.path.expanduser(value)
    return Path(expanded).resolve(strict=False)


def set_allowed_directories(dirs: list[str]) -> None:
    global _allowed_primary, _allowed_expanded
    primary = [normalize_path(d.strip()) for d in dirs if d and d.strip()]
    expanded: list[Path] = []
    for path in primary:
        expanded.append(path)
        try:
            real = path.resolve(strict=True)
        except OSError:
            continue
        if _norm_string(real) != _norm_string(path):
            expanded.append(real)
    _allowed_primary = _dedupe(primary)
    _allowed_expanded = _dedupe(expanded)


def get_allowed_directories() -> list[str]:
    return [str(path) for path in _allowed_expanded]


def _inside(candidate: Path, root: Path) -> bool:
    cand = _norm_string(candidate)
    base = _norm_string(root)
    if cand == base:
        return True
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _roots_for_relative() -> list[Path]:
    return _allowed_primary or _allowed_expanded


def _ensure_non_empty(value: str) -> None:
    if not value or not value.strip():
        raise FilesystemMcpError(ErrorCode.INVALID_INPUT, "Path cannot be empty or whitespace", value)


def _ensure_no_null(value: str) -> None:
    if "\0" in value:
        raise FilesystemMcpError(ErrorCode.INVALID_INPUT, "Path contains null bytes", value)


def _reserved_device_name(segment: str) -> str | None:
    trimmed = segment.rstrip(" .")
    without_stream = trimmed.split(":", 1)[0]
    base = without_stream.split(".", 1)[0].upper()
    return base if base in RESERVED_DEVICE_NAMES else None


def _ensure_windows_path_safe(value: str) -> None:
    if not IS_WINDOWS:
        return
    parsed_drive, tail = os.path.splitdrive(value)
    if parsed_drive and tail and not tail.startswith(("\\", "/")):
        raise FilesystemMcpError(
            ErrorCode.INVALID_INPUT,
            "Drive-relative path not allowed. Use C:\\path instead of C:path.",
            value,
        )
    for segment in re.split(r"[\\/]", value):
        reserved = _reserved_device_name(segment)
        if reserved:
            raise FilesystemMcpError(
                ErrorCode.INVALID_INPUT,
                f"Windows reserved device name not allowed: {reserved}",
                value,
            )


def resolve_requested_path(value: str) -> Path:
    _ensure_non_empty(value)
    _ensure_no_null(value)
    _ensure_windows_path_safe(value)
    expanded = os.path.expanduser(value)
    candidate = Path(expanded)
    if not candidate.is_absolute():
        roots = _roots_for_relative()
        if len(roots) > 1:
            raise FilesystemMcpError(
                ErrorCode.INVALID_INPUT,
                "Ambiguous relative path with multiple roots. Use an absolute path.",
                value,
            )
        if roots:
            candidate = roots[0] / candidate
    return candidate.resolve(strict=False)


def ensure_within_allowed(path: Path, requested: str) -> None:
    if not _allowed_expanded:
        raise FilesystemMcpError(
            ErrorCode.ACCESS_DENIED,
            "No allowed directories configured. Use --allow-cwd or configure roots.",
            requested,
        )
    if any(_inside(path, root) for root in _allowed_expanded):
        return
    raise FilesystemMcpError(ErrorCode.ACCESS_DENIED, "Outside allowed directories", requested)


def _match_any(patterns: list[str], candidates: list[str]) -> bool:
    for candidate in candidates:
        normalized = candidate.replace("\\", "/").lower()
        basename = Path(normalized).name
        for pattern in patterns:
            pat = pattern.replace("\\", "/").lower()
            if fnmatch.fnmatch(normalized, pat) or fnmatch.fnmatch(basename, pat):
                return True
            if "/" in pat and fnmatch.fnmatch(normalized, f"**/{pat.lstrip('/')}"):
                return True
    return False


def is_sensitive_path(requested: str, resolved: str | None = None) -> bool:
    candidates = [requested]
    if resolved and resolved != requested:
        candidates.append(resolved)
    if _match_any(SENSITIVE_FILE_ALLOWLIST, candidates):
        return False
    return _match_any(SENSITIVE_FILE_DENYLIST, candidates)


def assert_allowed_file_access(requested: str, resolved: str | None = None) -> None:
    if is_sensitive_path(requested, resolved):
        raise FilesystemMcpError(
            ErrorCode.ACCESS_DENIED,
            "Sensitive file blocked. Set FS_CONTEXT_ALLOW_SENSITIVE=1 to override.",
            requested,
        )


def validate_existing_path(requested: str) -> Path:
    candidate = resolve_requested_path(requested)
    ensure_within_allowed(candidate, requested)
    assert_allowed_file_access(requested, str(candidate))
    try:
        real = candidate.resolve(strict=True)
    except OSError as exc:
        raise FilesystemMcpError(ErrorCode.NOT_FOUND, "Path does not exist", requested) from exc
    ensure_within_allowed(real, requested)
    return real


def validate_existing_directory(requested: str | None) -> Path:
    path = validate_existing_path(requested or ".")
    if not path.is_dir():
        raise FilesystemMcpError(ErrorCode.NOT_DIRECTORY, "Not a directory", requested or ".")
    return path


def validate_path_for_write(requested: str) -> Path:
    candidate = resolve_requested_path(requested)
    ensure_within_allowed(candidate, requested)
    assert_allowed_file_access(requested, str(candidate))
    current = candidate if candidate.exists() else candidate.parent
    while not current.exists() and current != current.parent:
        current = current.parent
    try:
        real = current.resolve(strict=True)
    except OSError as exc:
        raise FilesystemMcpError(ErrorCode.NOT_FOUND, "Path is not accessible", requested) from exc
    ensure_within_allowed(real, requested)
    return candidate
