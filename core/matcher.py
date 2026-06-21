import re
from fnmatch import fnmatch
from pathlib import Path


def relative_posix(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix() or "."
    except ValueError:
        return path.as_posix()


def should_exclude(path: Path, root: Path, patterns: list) -> bool:
    if not patterns:
        return False

    rel = relative_posix(path, root)
    name = path.name
    full = path.as_posix()
    candidates = (rel, name, full)
    for pattern in patterns:
        normalized = pattern.replace("\\", "/")
        if any(fnmatch(candidate, normalized) for candidate in candidates):
            return True
        if "/" not in normalized and normalized in rel.split("/"):
            return True
    return False


def pattern_matches(value: str, pattern: str, mode: str) -> bool:
    if mode == "contains":
        return pattern in value
    if mode == "regex":
        try:
            return re.search(pattern, value) is not None
        except re.error:
            return False
    return value == pattern


def target_name_matches(name: str, targets: list) -> bool:
    for target in targets:
        if pattern_matches(name, target["pattern"], target.get("match_mode", "exact")):
            return True
    return False


def file_matches_targets(name: str, ext_targets: list, file_targets: list) -> bool:
    lower_name = name.lower()
    for target in ext_targets:
        pattern = target["pattern"].lower()
        mode = target.get("match_mode", "exact")
        if mode == "exact" and lower_name.endswith(pattern):
            return True
        if mode != "exact" and pattern_matches(lower_name, pattern, mode):
            return True
    return target_name_matches(name, file_targets)
