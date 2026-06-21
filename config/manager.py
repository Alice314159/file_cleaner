import json
import re

from config.settings import (
    BUILTIN_TARGET_KEYS,
    CONFIG_FILE,
    DEFAULT_EXCLUDE_PATTERNS,
    DEFAULT_TARGET_BY_KEY,
    DEFAULT_TARGETS,
    HISTORICAL_FILE_TARGETS,
    MATCH_MODES,
    TARGET_TYPES,
)


def normalize_targets(targets: list) -> list:
    normalized = []
    for raw in targets or []:
        target = normalize_target(raw)
        if target:
            normalized.append(target)
    return normalized


def merge_targets_with_defaults(targets: list) -> list:
    """Keep the built-in target set complete while preserving user choices."""
    saved_targets = normalize_targets(targets)
    saved_by_key = {(t["type"], t["pattern"]): t for t in saved_targets}

    merged = []
    seen = set()
    for default in DEFAULT_TARGETS:
        key = (default["type"], default["pattern"])
        saved = saved_by_key.get(key)
        target = dict(default)
        if saved:
            target["enabled"] = saved["enabled"]
        merged.append(target)
        seen.add(key)

    for target in saved_targets:
        key = (target["type"], target["pattern"])
        if key in seen:
            continue
        target = dict(target)
        target["builtin"] = False
        merged.append(target)
        seen.add(key)

    return merged


def normalize_target(raw: dict):
    kind = str(raw.get("type", "ext")).strip().lower()
    pattern = str(raw.get("pattern", "")).strip()
    enabled = bool(raw.get("enabled", True))
    match_mode = str(raw.get("match_mode", "exact")).strip().lower()

    if not pattern:
        return None
    if kind not in TARGET_TYPES:
        kind = "ext"
    if match_mode not in MATCH_MODES:
        match_mode = "exact"

    if kind == "ext" and match_mode != "regex":
        pattern = pattern.lstrip("*").strip()
        if pattern in HISTORICAL_FILE_TARGETS or (not pattern.startswith(".") and "." in pattern):
            kind = "file"
        elif not pattern.startswith("."):
            pattern = "." + pattern
        else:
            pattern = pattern.lower()

    default_target = DEFAULT_TARGET_BY_KEY.get((kind, pattern))
    if "match_mode" not in raw and default_target:
        match_mode = default_target.get("match_mode", match_mode)

    builtin = bool(raw.get("builtin", (kind, pattern) in BUILTIN_TARGET_KEYS))
    target_id = str(raw.get("id", "")).strip()
    if not target_id and builtin and default_target:
        target_id = default_target["id"]
    if not target_id:
        target_id = make_target_id(kind, pattern, builtin)

    return {
        "id": target_id,
        "type": kind,
        "pattern": pattern,
        "enabled": enabled,
        "builtin": builtin,
        "match_mode": match_mode,
    }


def make_target_id(kind: str, pattern: str, builtin=False) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", f"{kind}_{pattern}".lower()).strip("_")
    if not slug:
        slug = "target"
    return slug if builtin else f"custom_{slug}"


def normalize_pattern_list(value) -> list:
    if isinstance(value, str):
        pieces = value.replace("\n", ",").replace(";", ",").split(",")
    elif isinstance(value, list):
        pieces = value
    else:
        pieces = []
    return [str(p).strip() for p in pieces if str(p).strip()]


def merge_pattern_defaults(patterns: list, defaults: list) -> list:
    merged = []
    seen = set()
    for pattern in list(defaults) + normalize_pattern_list(patterns):
        key = pattern.replace("\\", "/")
        if key in seen:
            continue
        merged.append(pattern)
        seen.add(key)
    return merged


def normalize_max_depth(value):
    text = str(value).strip()
    if not text:
        return ""
    try:
        depth = int(text)
    except ValueError:
        return ""
    return str(depth) if depth >= 0 else ""


def copy_default_config() -> dict:
    return {
        "recent_paths": [],
        "targets": [dict(t) for t in DEFAULT_TARGETS],
        "exclude_patterns": list(DEFAULT_EXCLUDE_PATTERNS),
        "exclude_defaults_applied": True,
        "max_depth": "",
    }


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            config["recent_paths"] = config.get("recent_paths", [])
            config["targets"] = merge_targets_with_defaults(config.get("targets", DEFAULT_TARGETS))
            excludes = normalize_pattern_list(config.get("exclude_patterns", []))
            if not config.get("exclude_defaults_applied"):
                excludes = merge_pattern_defaults(excludes, DEFAULT_EXCLUDE_PATTERNS)
                config["exclude_defaults_applied"] = True
            config["exclude_patterns"] = excludes
            config["max_depth"] = normalize_max_depth(config.get("max_depth", ""))
            if not config["targets"]:
                config["targets"] = [dict(t) for t in DEFAULT_TARGETS]
            return config
        except Exception:
            pass
    return copy_default_config()


def save_config(config: dict):
    try:
        config["targets"] = merge_targets_with_defaults(config.get("targets", DEFAULT_TARGETS))
        config["exclude_patterns"] = normalize_pattern_list(config.get("exclude_patterns", []))
        config["exclude_defaults_applied"] = bool(config.get("exclude_defaults_applied", True))
        config["max_depth"] = normalize_max_depth(config.get("max_depth", ""))
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
