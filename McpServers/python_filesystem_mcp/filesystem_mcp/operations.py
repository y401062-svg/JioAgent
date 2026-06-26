from __future__ import annotations

import base64
import difflib
import fnmatch
import hashlib
import json
import os
import re
import shutil
import stat as stat_module
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .lib.constants import (
    DEFAULT_EXCLUDE_PATTERNS,
    DEFAULT_SEARCH_MAX_FILES,
    KNOWN_BINARY_EXTENSIONS,
    MAX_LINE_CONTENT_LENGTH,
    MAX_SEARCHABLE_FILE_SIZE,
    MAX_TEXT_FILE_SIZE,
    get_mime_type,
)
from .lib.errors import ErrorCode, FilesystemMcpError, error_result
from .lib.paths import validate_existing_directory, validate_existing_path, validate_path_for_write


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat().replace("+00:00", "Z")


def file_type(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if path.is_file():
        return "file"
    if path.is_dir():
        return "directory"
    return "other"


def relpath(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix() if path != root else "."


def is_hidden(path: Path, root: Path | None = None) -> bool:
    parts = path.relative_to(root).parts if root and path != root else path.parts
    return any(part.startswith(".") for part in parts if part not in {".", ".."})


def is_ignored(path: Path, root: Path, patterns: list[str] | None = None) -> bool:
    relative = relpath(path, root)
    pats = patterns if patterns is not None else DEFAULT_EXCLUDE_PATTERNS
    return any(fnmatch.fnmatch(relative, pat) or fnmatch.fnmatch(path.as_posix(), pat) for pat in pats)


def is_binary(path: Path) -> bool:
    if path.suffix.lower() in KNOWN_BINARY_EXTENSIONS:
        return True
    try:
        sample = path.read_bytes()[:512]
    except OSError:
        return False
    return b"\0" in sample


def safe_glob(pattern: str) -> None:
    if not pattern or len(pattern) > 1000:
        raise FilesystemMcpError(ErrorCode.INVALID_PATTERN, "Pattern required")
    p = pattern.replace("\\", "/")
    if p.startswith("/") or re.match(r"^[A-Za-z]:/", p) or "../" in f"/{p}/":
        raise FilesystemMcpError(ErrorCode.INVALID_PATTERN, "Invalid glob or unsafe path")


def match_glob(relative: str, pattern: str) -> bool:
    normalized = relative.replace("\\", "/")
    pat = pattern.replace("\\", "/")
    if fnmatch.fnmatch(normalized, pat):
        return True
    if pat.startswith("**/") and fnmatch.fnmatch(normalized, pat[3:]):
        return True
    return False


def sort_paths(paths: list[Path], root: Path, sort_by: str) -> list[Path]:
    def key(path: Path) -> Any:
        try:
            st = path.stat()
        except OSError:
            st = None
        if sort_by == "size":
            return (st.st_size if st else 0, path.name.lower())
        if sort_by == "modified":
            return (st.st_mtime if st else 0, path.name.lower())
        if sort_by == "type":
            return (file_type(path), path.name.lower())
        if sort_by == "path":
            return relpath(path, root).lower()
        return path.name.lower()

    return sorted(paths, key=key)


def list_directory_entries(
    path: str | None,
    *,
    include_hidden: bool = False,
    include_ignored: bool = False,
    max_depth: int | None = None,
    max_entries: int = 20000,
    sort_by: str = "name",
    pattern: str | None = None,
) -> dict[str, Any]:
    root = validate_existing_directory(path)
    if pattern:
        safe_glob(pattern)
        depth_limit = max_depth if max_depth is not None else 10
        candidates = [
            p
            for p in root.rglob("*")
            if len(p.relative_to(root).parts) <= depth_limit and match_glob(relpath(p, root), pattern)
        ]
    else:
        candidates = list(root.iterdir())
    visible: list[Path] = []
    skipped = 0
    for item in candidates:
        try:
            if not include_hidden and is_hidden(item, root):
                continue
            if not include_ignored and is_ignored(item, root):
                continue
            visible.append(item)
        except OSError:
            skipped += 1
    visible = sort_paths(visible, root, sort_by)
    truncated = len(visible) > max_entries
    shown = visible[:max_entries]
    entries = []
    for item in shown:
        try:
            st = item.stat()
        except OSError:
            skipped += 1
            continue
        entries.append(
            {
                "name": item.name,
                "relativePath": relpath(item, root),
                "type": file_type(item),
                "size": st.st_size if item.is_file() else 0,
                "modified": iso(st.st_mtime),
            }
        )
    return {
        "ok": True,
        "path": str(root),
        "entries": entries,
        "totalEntries": len(visible),
        "truncated": truncated,
        "totalFiles": sum(1 for p in visible if p.is_file()),
        "totalDirectories": sum(1 for p in visible if p.is_dir()),
        "skippedInaccessible": skipped,
        **({"stoppedReason": "maxEntries"} if truncated else {}),
    }


def stat_path(path: str) -> dict[str, Any]:
    resolved = validate_existing_path(path)
    st = resolved.stat()
    info: dict[str, Any] = {
        "name": resolved.name,
        "path": str(resolved),
        "type": file_type(resolved),
        "size": st.st_size,
        "tokenEstimate": max(0, st.st_size // 4),
        "created": iso(st.st_ctime),
        "modified": iso(st.st_mtime),
        "accessed": iso(st.st_atime),
        "permissions": stat_module.filemode(st.st_mode),
        "isHidden": resolved.name.startswith("."),
    }
    if resolved.is_file():
        info["mimeType"] = get_mime_type(resolved.suffix)
    if resolved.is_symlink():
        info["symlinkTarget"] = os.readlink(resolved)
    return {"ok": True, "info": info}


def read_file_content(
    path: str,
    *,
    head: int | None = None,
    tail: int | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
    include_hash: bool = False,
) -> dict[str, Any]:
    resolved = validate_existing_path(path)
    if not resolved.is_file():
        raise FilesystemMcpError(ErrorCode.NOT_FILE, "Target is a directory, not a file.", path)
    if resolved.stat().st_size > MAX_TEXT_FILE_SIZE and not any([head, tail, start_line, end_line]):
        raise FilesystemMcpError(ErrorCode.TOO_LARGE, "File too large", path)
    if is_binary(resolved):
        raise FilesystemMcpError(ErrorCode.NOT_FILE, "Binary file cannot be read as text", path)
    text = resolved.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    total = len(lines)
    result_lines = lines
    meta: dict[str, Any] = {"ok": True, "path": path, "totalLines": total}
    if head is not None:
        result_lines = lines[:head]
        meta.update({"head": head, "hasMoreLines": total > head})
    elif tail is not None:
        result_lines = lines[-tail:]
        meta.update({"tail": tail, "hasMoreLines": total > tail})
    elif start_line is not None or end_line is not None:
        start = start_line or 1
        end = end_line or total
        result_lines = lines[start - 1 : end]
        meta.update({"startLine": start, "endLine": min(end, total), "hasMoreLines": end < total})
    content = "\n".join(result_lines)
    meta["content"] = content
    meta["linesRead"] = len(result_lines)
    if include_hash:
        meta["contentHash"] = sha256_file(resolved)
    return meta


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def calculate_hash_path(path: str) -> dict[str, Any]:
    resolved = validate_existing_path(path)
    if resolved.is_file():
        return {"ok": True, "path": path, "hash": sha256_file(resolved), "isDirectory": False}
    digest = hashlib.sha256()
    count = 0
    for item in sorted(p for p in resolved.rglob("*") if p.is_file()):
        digest.update(relpath(item, resolved).encode())
        digest.update(sha256_file(item).encode())
        count += 1
    return {
        "ok": True,
        "path": path,
        "hash": digest.hexdigest(),
        "isDirectory": True,
        "fileCount": count,
    }


def find_files(
    path: str | None,
    pattern: str,
    *,
    max_results: int = 100,
    include_hidden: bool = False,
    include_ignored: bool = False,
    sort_by: str = "path",
    max_depth: int | None = None,
) -> dict[str, Any]:
    safe_glob(pattern)
    root = validate_existing_directory(path)
    results = []
    scanned = 0
    skipped = 0
    for item in root.rglob("*"):
        try:
            depth = len(item.relative_to(root).parts)
            if max_depth is not None and depth > max_depth:
                continue
            if not include_hidden and is_hidden(item, root):
                continue
            if not include_ignored and is_ignored(item, root):
                continue
            scanned += 1
            if match_glob(relpath(item, root), pattern):
                st = item.stat()
                results.append({"path": relpath(item, root), "size": st.st_size, "modified": iso(st.st_mtime)})
        except OSError:
            skipped += 1
    ordered = results
    if sort_by in {"name", "path"}:
        ordered = sorted(results, key=lambda r: Path(r["path"]).name.lower() if sort_by == "name" else r["path"].lower())
    elif sort_by == "size":
        ordered = sorted(results, key=lambda r: r["size"])
    elif sort_by == "modified":
        ordered = sorted(results, key=lambda r: r["modified"])
    truncated = len(ordered) > max_results
    return {
        "ok": True,
        "root": str(root),
        "results": ordered[:max_results],
        "totalMatches": len(ordered),
        "truncated": truncated,
        "filesScanned": scanned,
        "skippedInaccessible": skipped,
        **({"stoppedReason": "maxResults"} if truncated else {}),
    }


def grep_content(
    path: str | None,
    pattern: str,
    *,
    is_regex: bool = False,
    case_sensitive: bool = False,
    whole_word: bool = False,
    context_lines: int = 0,
    max_results: int = 500,
    file_pattern: str = "**/*",
    include_hidden: bool = False,
    include_ignored: bool = False,
) -> dict[str, Any]:
    safe_glob(file_pattern)
    root = validate_existing_directory(path)
    flags = 0 if case_sensitive else re.IGNORECASE
    needle = pattern if is_regex else re.escape(pattern)
    if whole_word:
        needle = rf"\b(?:{needle})\b"
    try:
        regex = re.compile(needle, flags)
    except re.error as exc:
        raise FilesystemMcpError(ErrorCode.INVALID_PATTERN, str(exc)) from exc
    matches = []
    files_scanned = files_matched = skipped_binary = skipped_large = skipped_inaccessible = 0
    for item in root.rglob("*"):
        if not item.is_file():
            continue
        relative = relpath(item, root)
        if not match_glob(relative, file_pattern):
            continue
        if not include_hidden and is_hidden(item, root):
            continue
        if not include_ignored and is_ignored(item, root):
            continue
        try:
            if item.stat().st_size > MAX_SEARCHABLE_FILE_SIZE:
                skipped_large += 1
                continue
            if is_binary(item):
                skipped_binary += 1
                continue
            lines = item.read_text(encoding="utf-8", errors="replace").splitlines()
            files_scanned += 1
        except OSError:
            skipped_inaccessible += 1
            continue
        file_had_match = False
        for index, line in enumerate(lines):
            found = list(regex.finditer(line))
            if not found:
                continue
            file_had_match = True
            content = line if len(line) <= MAX_LINE_CONTENT_LENGTH else line[:MAX_LINE_CONTENT_LENGTH]
            entry: dict[str, Any] = {
                "file": relative,
                "line": index + 1,
                "column": found[0].start(),
                "content": content,
                "matchCount": len(found),
            }
            if context_lines:
                entry["contextBefore"] = lines[max(0, index - context_lines) : index]
                entry["contextAfter"] = lines[index + 1 : index + 1 + context_lines]
            matches.append(entry)
            if len(matches) >= max_results:
                return {
                    "ok": True,
                    "matches": matches,
                    "totalMatches": len(matches),
                    "truncated": True,
                    "filesScanned": files_scanned,
                    "filesMatched": files_matched + int(file_had_match),
                    "skippedTooLarge": skipped_large,
                    "skippedBinary": skipped_binary,
                    "skippedInaccessible": skipped_inaccessible,
                    "stoppedReason": "maxResults",
                }
        if file_had_match:
            files_matched += 1
    return {
        "ok": True,
        "matches": matches,
        "totalMatches": len(matches),
        "truncated": False,
        "filesScanned": files_scanned,
        "filesMatched": files_matched,
        "skippedTooLarge": skipped_large,
        "skippedBinary": skipped_binary,
        "skippedInaccessible": skipped_inaccessible,
    }


def make_tree(path: str | None, *, max_depth: int = 5, max_entries: int = 1000, include_hidden: bool = False, include_ignored: bool = False, include_sizes: bool = False) -> dict[str, Any]:
    root = validate_existing_directory(path)
    count = 0
    truncated = False

    def build(node: Path, depth: int) -> dict[str, Any]:
        nonlocal count, truncated
        entry: dict[str, Any] = {"name": node.name or str(node), "type": file_type(node), "relativePath": relpath(node, root)}
        if include_sizes and node.is_file():
            entry["size"] = node.stat().st_size
        if depth >= max_depth or not node.is_dir():
            return entry
        children = []
        for child in sort_paths(list(node.iterdir()), root, "name"):
            if count >= max_entries:
                truncated = True
                break
            if not include_hidden and is_hidden(child, root):
                continue
            if not include_ignored and is_ignored(child, root):
                continue
            count += 1
            children.append(build(child, depth + 1))
        if children:
            entry["children"] = children
        return entry

    tree = build(root, 0)

    def lines(entry: dict[str, Any], prefix: str = "") -> list[str]:
        marker = "/" if entry["type"] == "directory" else ""
        output = [f"{prefix}{entry['name']}{marker}"]
        for child in entry.get("children", []):
            output.extend(lines(child, prefix + "  "))
        return output

    return {"ok": True, "root": str(root), "tree": tree, "ascii": "\n".join(lines(tree)), "truncated": truncated, "totalEntries": count}


def unified_diff(before: str, after: str, fromfile: str, tofile: str, context: int = 3) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=fromfile,
            tofile=tofile,
            n=context,
        )
    )


def diff_files(original: str, modified: str, *, context: int = 3, ignore_whitespace: bool = False, strip_trailing_cr: bool = False) -> dict[str, Any]:
    left_path = validate_existing_path(original)
    right_path = validate_existing_path(modified)
    left = left_path.read_text(encoding="utf-8", errors="replace")
    right = right_path.read_text(encoding="utf-8", errors="replace")
    if strip_trailing_cr:
        left = left.replace("\r\n", "\n").replace("\r", "\n")
        right = right.replace("\r\n", "\n").replace("\r", "\n")
    compare_left = "\n".join(line.strip() for line in left.splitlines()) if ignore_whitespace else left
    compare_right = "\n".join(line.strip() for line in right.splitlines()) if ignore_whitespace else right
    diff = unified_diff(compare_left, compare_right, original, modified, context)
    return {
        "ok": True,
        "diff": diff,
        "isIdentical": compare_left == compare_right,
        "linesAdded": sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")),
        "linesRemoved": sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")),
        "hunksCount": diff.count("\n@@ "),
        "truncated": False,
    }


def edit_file(path: str, edits: list[dict[str, str]], *, dry_run: bool = False, ignore_whitespace: bool = False) -> dict[str, Any]:
    target = validate_existing_path(path)
    before = target.read_text(encoding="utf-8", errors="replace")
    after = before
    unmatched: list[str] = []
    applied = 0
    for edit in edits:
        old = edit["oldText"]
        new = edit.get("newText", "")
        if old in after:
            after = after.replace(old, new, 1)
            applied += 1
            continue
        if ignore_whitespace:
            pattern = r"\s+".join(re.escape(part) for part in old.split())
            match = re.search(pattern, after)
            if match:
                after = after[: match.start()] + new + after[match.end() :]
                applied += 1
                continue
        unmatched.append(old)
    diff = unified_diff(before, after, path, path)
    if not dry_run and applied:
        write_target = validate_path_for_write(path)
        write_target.write_text(after, encoding="utf-8")
    return {
        "ok": not unmatched,
        "path": path,
        "appliedEdits": applied,
        "linesAdded": sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")),
        "linesRemoved": sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")),
        "unmatchedEdits": unmatched,
        "diff": diff,
    }


@dataclass
class Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str]


def parse_patch(patch: str) -> list[Hunk]:
    hunks: list[Hunk] = []
    current: Hunk | None = None
    header = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    for line in patch.splitlines():
        match = header.search(line)
        if match:
            if current:
                hunks.append(current)
            current = Hunk(int(match.group(1)), int(match.group(2) or "1"), int(match.group(3)), int(match.group(4) or "1"), [])
            continue
        if current is not None and (line.startswith((" ", "+", "-")) or line == "\\ No newline at end of file"):
            current.lines.append(line)
    if current:
        hunks.append(current)
    if not hunks:
        raise FilesystemMcpError(ErrorCode.INVALID_INPUT, "Patch must include hunk headers")
    return hunks


def apply_patch_to_file(path: str, patch: str, *, dry_run: bool = False, fuzz_factor: int = 0, auto_convert_line_endings: bool = True) -> dict[str, Any]:
    target = validate_existing_path(path)
    before = target.read_text(encoding="utf-8", errors="replace")
    lines = before.splitlines()
    offset = 0
    added = removed = applied = 0
    for hunk in parse_patch(patch):
        start = max(0, hunk.old_start - 1 + offset)
        expected = [line[1:] for line in hunk.lines if line.startswith((" ", "-"))]
        replacement = [line[1:] for line in hunk.lines if line.startswith((" ", "+"))]
        end = start + len(expected)
        if lines[start:end] != expected:
            if fuzz_factor <= 0:
                return {"ok": False, "path": path, "applied": False, "hunksApplied": applied}
            found = None
            for idx in range(max(0, start - fuzz_factor), min(len(lines), start + fuzz_factor + 1)):
                if lines[idx : idx + len(expected)] == expected:
                    found = idx
                    break
            if found is None:
                return {"ok": False, "path": path, "applied": False, "hunksApplied": applied}
            start = found
            end = start + len(expected)
        lines[start:end] = replacement
        offset += len(replacement) - len(expected)
        added += sum(1 for line in hunk.lines if line.startswith("+"))
        removed += sum(1 for line in hunk.lines if line.startswith("-"))
        applied += 1
    after = "\n".join(lines)
    if before.endswith("\n"):
        after += "\n"
    if not dry_run:
        validate_path_for_write(path).write_text(after, encoding="utf-8")
    return {"ok": True, "path": path, "applied": True, "hunksApplied": applied, "linesAdded": added, "linesRemoved": removed}


def search_replace(path: str | None, *, file_pattern: str, search_pattern: str, replacement: str, is_regex: bool = False, case_sensitive: bool = True, dry_run: bool = False, include_hidden: bool = False, include_ignored: bool = False, return_diff: bool = False, max_files: int | None = None) -> dict[str, Any]:
    root = validate_existing_directory(path)
    safe_glob(file_pattern)
    flags = 0 if case_sensitive else re.IGNORECASE
    regex = re.compile(search_pattern if is_regex else re.escape(search_pattern), flags)
    processed = matches = changed = failed = 0
    changed_files: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    diffs: list[str] = []
    for item in root.rglob("*"):
        if max_files is not None and processed >= max_files:
            break
        if not item.is_file() or not match_glob(relpath(item, root), file_pattern):
            continue
        if not include_hidden and is_hidden(item, root):
            continue
        if not include_ignored and is_ignored(item, root):
            continue
        processed += 1
        try:
            before = item.read_text(encoding="utf-8", errors="replace")
            after, count = regex.subn(replacement, before)
        except Exception as exc:
            failed += 1
            if len(failures) < 20:
                failures.append({"path": relpath(item, root), "error": error_result(exc, str(item))})
            continue
        if count:
            matches += count
            changed += 1
            changed_files.append({"path": relpath(item, root), "matches": count})
            if dry_run or return_diff:
                diffs.append(unified_diff(before, after, str(item), str(item)))
            if not dry_run:
                validate_path_for_write(str(item)).write_text(after, encoding="utf-8")
    return {
        "ok": True,
        "matches": matches,
        "filesChanged": changed,
        "processedFiles": processed,
        "failedFiles": failed,
        "failures": failures,
        "changedFiles": changed_files[:100],
        "changedFilesTruncated": len(changed_files) > 100,
        "diff": "\n".join(diffs) if diffs else None,
        "diffTruncated": False,
        **({"stoppedReason": "maxFiles"} if max_files is not None and processed >= max_files else {}),
    }


def encode_cursor(payload: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
