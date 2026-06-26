from __future__ import annotations

import os

KIB = 1024
MIB = 1024 * KIB


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = os.environ.get(name)
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if minimum <= parsed <= maximum else default


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_list(name: str) -> list[str]:
    value = os.environ.get(name, "")
    return [part.strip() for part in value.replace("\n", ",").split(",") if part.strip()]


MAX_SEARCHABLE_FILE_SIZE = _env_int("MAX_SEARCH_SIZE", MIB, 100 * KIB, 10 * MIB)
MAX_TEXT_FILE_SIZE = _env_int("MAX_FILE_SIZE", 10 * MIB, MIB, 100 * MIB)
DEFAULT_READ_MANY_MAX_TOTAL_SIZE = _env_int(
    "MAX_READ_MANY_TOTAL_SIZE", 512 * KIB, 10 * KIB, 100 * MIB
)
DEFAULT_SEARCH_TIMEOUT_MS = _env_int("DEFAULT_SEARCH_TIMEOUT", 5000, 100, 60000)

DEFAULT_MAX_DEPTH = 10
DEFAULT_LIST_MAX_ENTRIES = 20000
DEFAULT_SEARCH_MAX_FILES = 20000
MAX_TREE_DEPTH = 50
DEFAULT_TREE_DEPTH = 5
MAX_TREE_ENTRIES = 20000
DEFAULT_TREE_ENTRIES = 1000
MAX_LIST_ENTRIES = 20000
MAX_SEARCH_RESULTS = 10000
DEFAULT_SEARCH_RESULTS = 100
MAX_SEARCH_DEPTH = 100
DEFAULT_SEARCH_CONTENT_RESULTS = 500
MAX_LINE_CONTENT_LENGTH = 200
BINARY_CHECK_BUFFER_SIZE = 512

DEFAULT_SENSITIVE_PATTERNS = [
    ".env",
    ".env.*",
    ".npmrc",
    ".pypirc",
    ".aws/credentials",
    ".aws/config",
    ".mcpregistry_*_token",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.crt",
    "*.cer",
    "*id_rsa*",
    "*id_dsa*",
]

SENSITIVE_FILE_DENYLIST = (
    [] if _env_bool("FS_CONTEXT_ALLOW_SENSITIVE") else DEFAULT_SENSITIVE_PATTERNS
) + _env_list("FS_CONTEXT_DENYLIST")
SENSITIVE_FILE_ALLOWLIST = _env_list("FS_CONTEXT_ALLOWLIST")

DEFAULT_EXCLUDE_PATTERNS = [
    "**/node_modules",
    "**/node_modules/**",
    "**/dist",
    "**/dist/**",
    "**/build",
    "**/build/**",
    "**/coverage",
    "**/coverage/**",
    "**/.git",
    "**/.git/**",
    "**/.vscode",
    "**/.vscode/**",
    "**/.idea",
    "**/.idea/**",
    "**/.DS_Store",
    "**/.next",
    "**/.next/**",
    "**/.nuxt",
    "**/.nuxt/**",
    "**/.output",
    "**/.output/**",
    "**/.svelte-kit",
    "**/.svelte-kit/**",
    "**/.cache",
    "**/.cache/**",
    "**/.yarn",
    "**/.yarn/**",
    "**/jspm_packages",
    "**/jspm_packages/**",
    "**/bower_components",
    "**/bower_components/**",
    "**/out",
    "**/out/**",
    "**/tmp",
    "**/tmp/**",
    "**/.temp",
    "**/.temp/**",
    "**/npm-debug.log",
    "**/yarn-debug.log",
    "**/yarn-error.log",
    "**/Thumbs.db",
]

KNOWN_BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".ico",
    ".mp3",
    ".wav",
    ".flac",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".sqlite",
    ".db",
    ".wasm",
    ".bin",
    ".dat",
}

MIME_TYPES = {
    ".txt": "text/plain",
    ".log": "text/plain",
    ".md": "text/markdown",
    ".json": "application/json",
    ".jsonc": "application/json",
    ".xml": "application/xml",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
    ".html": "text/html",
    ".htm": "text/html",
    ".css": "text/css",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".cjs": "text/javascript",
    ".ts": "text/typescript",
    ".tsx": "text/typescript",
    ".py": "text/x-python",
    ".svg": "image/svg+xml",
}


def get_mime_type(ext: str) -> str:
    return MIME_TYPES.get(ext.lower(), "application/octet-stream")
