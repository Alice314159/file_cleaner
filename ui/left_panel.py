from config.settings import COLORS


def target_risk(target: dict) -> tuple:
    pattern = target.get("pattern", "")
    kind = target.get("type", "")

    high_risk = {
        ".git", ".hg", ".svn", ".ssh", ".gnupg", "System", "Library",
        "Windows", "Program Files", "Users", "Applications",
    }
    medium_risk = {
        "node_modules", "dist", "build", ".venv", "venv", "target",
        "coverage", ".next", ".nuxt", ".cache",
    }

    if pattern in high_risk or (kind == "folder" and pattern.startswith(".git")):
        return ("HIGH", COLORS["high_risk"])
    if pattern in medium_risk or pattern.endswith(".egg-info"):
        return ("MED", COLORS["med_risk"])
    return ("LOW", COLORS["low_risk"])
