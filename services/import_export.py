import json

from config.manager import normalize_max_depth, normalize_pattern_list, normalize_targets


def export_payload(config: dict) -> dict:
    return {
        "targets": normalize_targets(config.get("targets", [])),
        "exclude_patterns": normalize_pattern_list(config.get("exclude_patterns", [])),
        "max_depth": normalize_max_depth(config.get("max_depth", "")),
    }


def write_rules(path: str, config: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(export_payload(config), f, ensure_ascii=False, indent=2)


def read_rules(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return {
        "targets": normalize_targets(payload.get("targets", [])),
        "exclude_patterns": normalize_pattern_list(payload.get("exclude_patterns", [])),
        "max_depth": normalize_max_depth(payload.get("max_depth", "")),
    }
