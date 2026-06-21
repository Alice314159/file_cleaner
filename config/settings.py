from pathlib import Path


CONFIG_FILE = Path.home() / ".file_cleaner_config.json"
FAST_SCAN_MODE = True

DEFAULT_EXCLUDE_PATTERNS = [
    ".venv",
    "venv",
    "env",
    "ENV",
    "virtualenv",
    ".tox",
    ".nox",
]

DEFAULT_TARGETS = [
    {"id": "pycache",      "type": "folder", "pattern": "__pycache__",   "enabled": True,  "builtin": True, "match_mode": "exact"},
    {"id": "pytest_cache", "type": "folder", "pattern": ".pytest_cache", "enabled": True,  "builtin": True, "match_mode": "exact"},
    {"id": "mypy_cache",   "type": "folder", "pattern": ".mypy_cache",   "enabled": True,  "builtin": True, "match_mode": "exact"},
    {"id": "ruff_cache",   "type": "folder", "pattern": ".ruff_cache",   "enabled": True,  "builtin": True, "match_mode": "exact"},
    {"id": "node_modules", "type": "folder", "pattern": "node_modules",  "enabled": False, "builtin": True, "match_mode": "exact"},
    {"id": "dist",         "type": "folder", "pattern": "dist",          "enabled": False, "builtin": True, "match_mode": "exact"},
    {"id": "build",        "type": "folder", "pattern": "build",         "enabled": False, "builtin": True, "match_mode": "exact"},
    {"id": "egg_info",     "type": "folder", "pattern": ".egg-info",     "enabled": True,  "builtin": True, "match_mode": "contains"},
    {"id": "pyc",          "type": "ext",    "pattern": ".pyc",          "enabled": True,  "builtin": True, "match_mode": "exact"},
    {"id": "pyo",          "type": "ext",    "pattern": ".pyo",          "enabled": True,  "builtin": True, "match_mode": "exact"},
    {"id": "pyd",          "type": "ext",    "pattern": ".pyd",          "enabled": False, "builtin": True, "match_mode": "exact"},
    {"id": "log",          "type": "ext",    "pattern": ".log",          "enabled": False, "builtin": True, "match_mode": "exact"},
    {"id": "tmp",          "type": "ext",    "pattern": ".tmp",          "enabled": False, "builtin": True, "match_mode": "exact"},
    {"id": "coverage_file", "type": "file",   "pattern": ".coverage",    "enabled": True,  "builtin": True, "match_mode": "exact"},
    {"id": "ds_store",     "type": "file",   "pattern": ".DS_Store",     "enabled": True,  "builtin": True, "match_mode": "exact"},
    {"id": "thumbs_db",    "type": "file",   "pattern": "Thumbs.db",     "enabled": True,  "builtin": True, "match_mode": "exact"},
]

TARGET_TYPES = {"folder", "ext", "file"}
MATCH_MODES = {"exact", "contains", "regex"}
HISTORICAL_FILE_TARGETS = {".DS_Store", "Thumbs.db"}
BUILTIN_TARGET_KEYS = {(t["type"], t["pattern"]) for t in DEFAULT_TARGETS}
DEFAULT_TARGET_BY_KEY = {(t["type"], t["pattern"]): t for t in DEFAULT_TARGETS}
DANGEROUS_FOLDER_PATTERNS = {
    "", ".", "..", "/", "\\", "~", ".git", ".hg", ".svn", ".ssh", ".gnupg",
}

COLORS = {
    "bg": "#14171D",
    "surface": "#191D24",
    "panel": "#1F242D",
    "card": "#272D38",
    "card_hover": "#303746",
    "border": "#38404D",
    "accent": "#3B82F6",
    "accent_hover": "#5A96FF",
    "danger": "#D9534F",
    "danger_hover": "#EB6B66",
    "success": "#31B979",
    "success_hover": "#45CC8C",
    "warning": "#F2A93B",
    "text": "#EEF2F7",
    "text_dim": "#A7AFBD",
    "text_muted": "#6F7887",
    "disabled": "#3A404A",
    "disabled_text": "#7A828F",
    "folder_tag": "#7C5CBF",
    "ext_tag": "#287C9F",
    "file_tag": "#2F8F65",
    "row_alt": "#222832",
    "highlight": "#2F4566",
}
