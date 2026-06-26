from __future__ import annotations

import shutil
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .lib.errors import ErrorCode, FilesystemMcpError, error_result
from .lib.paths import get_allowed_directories, validate_path_for_write
from .operations import (
    apply_patch_to_file,
    calculate_hash_path,
    diff_files as diff_files_op,
    edit_file,
    find_files,
    grep_content,
    list_directory_entries,
    make_tree,
    read_file_content,
    search_replace,
    stat_path,
)

SERVER_INSTRUCTIONS = """Secure filesystem MCP server for reading, writing, searching, diffing, and patching files.
All file access is constrained to the configured allowed roots."""

TOOL_NAMES = [
    "roots",
    "ls",
    "find",
    "tree",
    "read",
    "read_many",
    "stat",
    "stat_many",
    "grep",
    "mkdir",
    "write",
    "edit",
    "mv",
    "rm",
    "calculate_hash",
    "diff_files",
    "apply_patch",
    "search_and_replace",
]

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
IDEMPOTENT_WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)
DESTRUCTIVE_WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=False)


def _wrap_error(exc: Exception, path: str | None = None) -> dict[str, Any]:
    err = error_result(exc, path)
    return {"ok": False, "error": err}


def create_server(*, port: int | None = None) -> FastMCP:
    mcp = FastMCP(
        "io.github.j0hanz/filesystem-mcp",
        instructions=SERVER_INSTRUCTIONS,
        port=port or 8000,
        streamable_http_path="/mcp",
    )

    @mcp.tool(name="roots", description="List allowed workspace roots.", annotations=READ_ONLY, structured_output=True)
    def roots() -> dict[str, Any]:
        return {"ok": True, "directories": get_allowed_directories()}

    @mcp.tool(name="ls", description="List directory entries.", annotations=READ_ONLY, structured_output=True)
    def ls(
        path: str | None = None,
        includeHidden: bool = False,
        includeIgnored: bool = False,
        maxDepth: int | None = None,
        maxEntries: int = 20000,
        sortBy: str = "name",
        pattern: str | None = None,
        includeSymlinkTargets: bool = False,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        del includeSymlinkTargets, cursor
        try:
            return list_directory_entries(
                path,
                include_hidden=includeHidden,
                include_ignored=includeIgnored,
                max_depth=maxDepth,
                max_entries=maxEntries,
                sort_by=sortBy,
                pattern=pattern,
            )
        except Exception as exc:
            return _wrap_error(exc, path)

    @mcp.tool(name="find", description="Search files by safe glob.", annotations=READ_ONLY, structured_output=True)
    def find(
        pattern: str,
        path: str | None = None,
        maxResults: int = 100,
        includeIgnored: bool = False,
        includeHidden: bool = False,
        sortBy: str = "path",
        maxDepth: int | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        del cursor
        try:
            return find_files(
                path,
                pattern,
                max_results=maxResults,
                include_hidden=includeHidden,
                include_ignored=includeIgnored,
                sort_by=sortBy,
                max_depth=maxDepth,
            )
        except Exception as exc:
            return _wrap_error(exc, path)

    @mcp.tool(name="tree", description="Return structured and ASCII directory tree.", annotations=READ_ONLY, structured_output=True)
    def tree(
        path: str | None = None,
        maxDepth: int = 5,
        maxEntries: int = 1000,
        includeHidden: bool = False,
        includeIgnored: bool = False,
        includeSizes: bool = False,
    ) -> dict[str, Any]:
        try:
            return make_tree(
                path,
                max_depth=maxDepth,
                max_entries=maxEntries,
                include_hidden=includeHidden,
                include_ignored=includeIgnored,
                include_sizes=includeSizes,
            )
        except Exception as exc:
            return _wrap_error(exc, path)

    @mcp.tool(name="read", description="Read text file contents.", annotations=READ_ONLY, structured_output=True)
    def read(
        path: str,
        head: int | None = None,
        tail: int | None = None,
        startLine: int | None = None,
        endLine: int | None = None,
        includeHash: bool = False,
    ) -> dict[str, Any]:
        try:
            return read_file_content(path, head=head, tail=tail, start_line=startLine, end_line=endLine, include_hash=includeHash)
        except Exception as exc:
            return _wrap_error(exc, path)

    @mcp.tool(name="read_many", description="Read multiple files.", annotations=READ_ONLY, structured_output=True)
    def read_many(
        paths: list[str],
        head: int | None = None,
        tail: int | None = None,
        startLine: int | None = None,
        endLine: int | None = None,
    ) -> dict[str, Any]:
        results = []
        succeeded = failed = 0
        for path in paths:
            try:
                result = read_file_content(path, head=head, tail=tail, start_line=startLine, end_line=endLine)
                results.append(result)
                succeeded += 1
            except Exception as exc:
                results.append({"path": path, "error": error_result(exc, path)})
                failed += 1
        return {"ok": True, "results": results, "summary": {"total": len(paths), "succeeded": succeeded, "failed": failed}}

    @mcp.tool(name="stat", description="Return metadata for one file or directory.", annotations=READ_ONLY, structured_output=True)
    def stat(path: str) -> dict[str, Any]:
        try:
            return stat_path(path)
        except Exception as exc:
            return _wrap_error(exc, path)

    @mcp.tool(name="stat_many", description="Return metadata for many paths.", annotations=READ_ONLY, structured_output=True)
    def stat_many(paths: list[str]) -> dict[str, Any]:
        results = []
        succeeded = failed = 0
        for path in paths:
            try:
                results.append({"path": path, "info": stat_path(path)["info"]})
                succeeded += 1
            except Exception as exc:
                results.append({"path": path, "error": error_result(exc, path)})
                failed += 1
        return {"ok": True, "results": results, "summary": {"total": len(paths), "succeeded": succeeded, "failed": failed}}

    @mcp.tool(name="grep", description="Search file content.", annotations=READ_ONLY, structured_output=True)
    def grep(
        pattern: str,
        path: str | None = None,
        isRegex: bool = False,
        caseSensitive: bool = False,
        wholeWord: bool = False,
        contextLines: int = 0,
        maxResults: int = 500,
        filePattern: str = "**/*",
        includeHidden: bool = False,
        includeIgnored: bool = False,
    ) -> dict[str, Any]:
        try:
            return grep_content(
                path,
                pattern,
                is_regex=isRegex,
                case_sensitive=caseSensitive,
                whole_word=wholeWord,
                context_lines=contextLines,
                max_results=maxResults,
                file_pattern=filePattern,
                include_hidden=includeHidden,
                include_ignored=includeIgnored,
            )
        except Exception as exc:
            return _wrap_error(exc, path)

    @mcp.tool(name="mkdir", description="Create one or more directories recursively.", annotations=IDEMPOTENT_WRITE, structured_output=True)
    def mkdir(path: str | None = None, paths: list[str] | None = None) -> dict[str, Any]:
        try:
            targets = paths if paths is not None else ([path] if path else [])
            if not targets:
                raise FilesystemMcpError(ErrorCode.INVALID_INPUT, "Either 'path' or 'paths' must be provided")
            created = []
            for target in targets:
                resolved = validate_path_for_write(target)
                resolved.mkdir(parents=True, exist_ok=True)
                created.append(str(resolved))
            return {"ok": True, "paths": created, **({"path": created[0]} if len(created) == 1 else {})}
        except Exception as exc:
            return _wrap_error(exc, path)

    @mcp.tool(name="write", description="Write full file content.", annotations=DESTRUCTIVE_WRITE, structured_output=True)
    def write(path: str, content: str) -> dict[str, Any]:
        try:
            resolved = validate_path_for_write(path)
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
            return {"ok": True, "path": path, "bytesWritten": len(content.encode("utf-8"))}
        except Exception as exc:
            return _wrap_error(exc, path)

    @mcp.tool(name="edit", description="Sequential literal text replacements.", annotations=DESTRUCTIVE_WRITE, structured_output=True)
    def edit(path: str, edits: list[dict[str, str]], dryRun: bool = False, ignoreWhitespace: bool = False) -> dict[str, Any]:
        try:
            return edit_file(path, edits, dry_run=dryRun, ignore_whitespace=ignoreWhitespace)
        except Exception as exc:
            return _wrap_error(exc, path)

    @mcp.tool(name="mv", description="Move or rename files/directories.", annotations=DESTRUCTIVE_WRITE, structured_output=True)
    def mv(destination: str, source: str | None = None, sources: list[str] | None = None) -> dict[str, Any]:
        try:
            items = sources if sources is not None else ([source] if source else [])
            if not items:
                raise FilesystemMcpError(ErrorCode.INVALID_INPUT, "Either 'source' or 'sources' must be provided")
            dest = validate_path_for_write(destination)
            failed = []
            moved = []
            for item in items:
                try:
                    src = validate_path_for_write(item)
                    target = dest / src.name if len(items) > 1 or dest.is_dir() else dest
                    validate_path_for_write(str(target))
                    shutil.move(str(src), str(target))
                    moved.append(item)
                except Exception as exc:
                    failed.append({"source": item, "error": error_result(exc, item)})
            return {"ok": not failed, "source": source, "sources": moved, "destination": destination, "failed": failed}
        except Exception as exc:
            return _wrap_error(exc, source or destination)

    @mcp.tool(name="rm", description="Delete file or directory.", annotations=DESTRUCTIVE_WRITE, structured_output=True)
    def rm(path: str, recursive: bool = False, ignoreIfNotExists: bool = False) -> dict[str, Any]:
        try:
            resolved = validate_path_for_write(path)
            if not resolved.exists():
                if ignoreIfNotExists:
                    return {"ok": True, "path": path}
                raise FilesystemMcpError(ErrorCode.NOT_FOUND, "Path does not exist", path)
            if resolved.is_dir():
                if recursive:
                    shutil.rmtree(resolved)
                else:
                    resolved.rmdir()
            else:
                resolved.unlink()
            return {"ok": True, "path": path}
        except Exception as exc:
            return _wrap_error(exc, path)

    @mcp.tool(name="calculate_hash", description="SHA-256 hash for file or directory.", annotations=READ_ONLY, structured_output=True)
    def calculate_hash(path: str) -> dict[str, Any]:
        try:
            return calculate_hash_path(path)
        except Exception as exc:
            return _wrap_error(exc, path)

    @mcp.tool(name="diff_files", description="Unified diff between two files.", annotations=READ_ONLY, structured_output=True)
    def diff_files(original: str, modified: str, context: int = 3, ignoreWhitespace: bool = False, stripTrailingCr: bool = False) -> dict[str, Any]:
        try:
            return diff_files_op(original, modified, context=context, ignore_whitespace=ignoreWhitespace, strip_trailing_cr=stripTrailingCr)
        except Exception as exc:
            return _wrap_error(exc, original)

    @mcp.tool(name="apply_patch", description="Apply unified diff hunks.", annotations=DESTRUCTIVE_WRITE, structured_output=True)
    def apply_patch(path: str, patch: str, fuzzFactor: int = 0, autoConvertLineEndings: bool = True, dryRun: bool = False) -> dict[str, Any]:
        try:
            return apply_patch_to_file(path, patch, dry_run=dryRun, fuzz_factor=fuzzFactor, auto_convert_line_endings=autoConvertLineEndings)
        except Exception as exc:
            return _wrap_error(exc, path)

    @mcp.tool(name="search_and_replace", description="Multi-file search/replace.", annotations=DESTRUCTIVE_WRITE, structured_output=True)
    def search_and_replace(
        searchPattern: str,
        replacement: str,
        path: str | None = None,
        filePattern: str = "**/*",
        isRegex: bool = False,
        caseSensitive: bool = True,
        dryRun: bool = False,
        includeHidden: bool = False,
        includeIgnored: bool = False,
        returnDiff: bool = False,
        maxFiles: int | None = None,
    ) -> dict[str, Any]:
        try:
            return search_replace(
                path,
                file_pattern=filePattern,
                search_pattern=searchPattern,
                replacement=replacement,
                is_regex=isRegex,
                case_sensitive=caseSensitive,
                dry_run=dryRun,
                include_hidden=includeHidden,
                include_ignored=includeIgnored,
                return_diff=returnDiff,
                max_files=maxFiles,
            )
        except Exception as exc:
            return _wrap_error(exc, path)

    @mcp.resource("internal://instructions", name="instructions", mime_type="text/plain")
    def instructions() -> str:
        return SERVER_INSTRUCTIONS

    @mcp.resource("internal://tool-catalog", name="tool-catalog", mime_type="application/json")
    def tool_catalog() -> dict[str, Any]:
        return {"tools": TOOL_NAMES}

    @mcp.resource("internal://workflows", name="workflows", mime_type="text/plain")
    def workflows() -> str:
        return "Use roots first, inspect with ls/find/stat/read, and dry-run edit/apply_patch/search_and_replace before destructive writes."

    @mcp.resource("internal://metrics", name="metrics", mime_type="application/json")
    def metrics() -> dict[str, Any]:
        return {"implementation": "python", "toolCount": len(TOOL_NAMES)}

    @mcp.resource("internal://tool-info/{name}", name="tool-info", mime_type="application/json")
    def tool_info(name: str) -> dict[str, Any]:
        return {"name": name, "available": name in TOOL_NAMES}

    @mcp.prompt(name="get_help", description="Filesystem MCP help.")
    def get_help() -> str:
        return "List roots, inspect paths with ls/find/stat/read, and use dryRun for edit/apply_patch/search_and_replace previews."

    @mcp.prompt(name="compare_files", description="Compare two files.")
    def compare_files(original: str, modified: str) -> str:
        return f"Use diff_files with original={original!r} and modified={modified!r}."

    @mcp.prompt(name="analyze_path", description="Analyze a path.")
    def analyze_path(path: str) -> str:
        return f"Use stat, ls or read as appropriate for {path!r}; then summarize important findings."

    @mcp.prompt(name="tool_help", description="Help for a tool.")
    def tool_help(name: str) -> str:
        return f"Tool {name!r} is {'available' if name in TOOL_NAMES else 'not registered'} in the Python implementation."

    return mcp
