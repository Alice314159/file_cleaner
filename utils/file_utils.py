from pathlib import Path


def get_modified(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except Exception:
        return 0.0
