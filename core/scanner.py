import os
from pathlib import Path

from config.manager import normalize_pattern_list, normalize_targets
from core.matcher import file_matches_targets, relative_posix, should_exclude, target_name_matches
from utils.file_utils import get_modified
from utils.logger import LOGGER


def scan_targets(
        root_path: str,
        targets: list,
        exclude_patterns=None,
        max_depth=None,
        progress_callback=None,
        result_callback=None,
        stop_event=None,
) -> list:
    results = []
    root = Path(root_path)
    exclude_patterns = normalize_pattern_list(exclude_patterns or [])
    max_depth_value = int(max_depth) if str(max_depth).strip().isdigit() else None

    clean_targets = normalize_targets(targets)
    enabled_folders = [t for t in clean_targets if t["type"] == "folder" and t["enabled"]]
    enabled_exts = [t for t in clean_targets if t["type"] == "ext" and t["enabled"]]
    enabled_files = [t for t in clean_targets if t["type"] == "file" and t["enabled"]]

    scanned_dirs = 0
    LOGGER.info("scan start root=%s", root_path)

    def is_stopped():
        return stop_event is not None and stop_event.is_set()

    def add_result(item):
        results.append(item)
        if result_callback:
            result_callback(item)

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        if is_stopped():
            break

        dp = Path(dirpath)
        scanned_dirs += 1
        if scanned_dirs % 50 == 0 and progress_callback:
            progress_callback(scanned_dirs, len(results), str(dp))

        if should_exclude(dp, root, exclude_patterns):
            dirnames.clear()
            continue

        rel_dir = relative_posix(dp, root)
        depth = 0 if rel_dir == "." else len(Path(rel_dir).parts)
        if max_depth_value is not None and depth >= max_depth_value:
            dirnames.clear()

        dirnames[:] = [
            d for d in dirnames
            if not should_exclude(dp / d, root, exclude_patterns)
        ]
        filenames = [
            f for f in filenames
            if not should_exclude(dp / f, root, exclude_patterns)
        ]

        for d in list(dirnames):
            if is_stopped():
                break
            full = dp / d
            if target_name_matches(d, enabled_folders):
                add_result({
                    "path": str(full),
                    "kind": "folder",
                    "name": d,
                    "size": 0,
                    "modified": get_modified(full),
                })
                dirnames.remove(d)

        for fname in filenames:
            if is_stopped():
                break
            if not file_matches_targets(fname, enabled_exts, enabled_files):
                continue
            full = dp / fname
            try:
                add_result({
                    "path": str(full),
                    "kind": "file",
                    "name": fname,
                    "size": full.stat().st_size,
                    "modified": get_modified(full),
                })
            except Exception:
                pass

    LOGGER.info("scan complete folders=%s results=%s", scanned_dirs, len(results))
    return results
