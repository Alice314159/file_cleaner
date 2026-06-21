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
    "bg": "#111113",
    "surface": "#151517",
    "panel": "#18181A",
    "card": "#1F1F23",
    "card_hover": "#282830",
    "border": "#2A2A31",
    "border_soft": "#232329",
    "accent": "#6D5DFC",
    "accent_hover": "#7B6DFF",
    "accent_soft": "#2A2556",
    "danger": "#EF4444",
    "danger_hover": "#F87171",
    "danger_soft": "#2A1619",
    "success": "#5BA56B",
    "success_hover": "#6DB87C",
    "warning": "#D6A13D",
    "text": "#E6E6EA",
    "text_dim": "#A4A4AD",
    "text_muted": "#6F6F78",
    "disabled": "#242428",
    "disabled_text": "#777781",
    "folder_tag": "#8B7CFF",
    "ext_tag": "#8B7CFF",
    "file_tag": "#8B7CFF",
    "low_risk": "#315338",
    "med_risk": "#5A4420",
    "high_risk": "#5A2629",
    "row_hover": "#202029",
    "highlight": "#2A2556",
}
