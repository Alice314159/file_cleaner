def save_recent_path(config: dict, path: str, limit=15) -> list:
    paths = config.get("recent_paths", [])
    if path in paths:
        paths.remove(path)
    paths.insert(0, path)
    paths = paths[:limit]
    config["recent_paths"] = paths
    return paths
