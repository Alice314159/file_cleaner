import shutil
import subprocess
import sys
from pathlib import Path

from utils.logger import LOGGER


def delete_item(path: str) -> bool:
    try:
        p = Path(path)
        if not p.exists():
            LOGGER.warning("trash failed path missing=%s", path)
            return False
        return move_to_trash(p)
    except Exception:
        LOGGER.exception("trash failed unexpected path=%s", path)
        return False


def move_to_trash(path: Path) -> bool:
    if sys.platform == "darwin":
        return move_to_macos_trash(path)

    if sys.platform == "win32":
        return move_to_windows_recycle_bin(path)

    for cmd in (["gio", "trash", str(path)], ["trash-put", str(path)]):
        if shutil.which(cmd[0]):
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                LOGGER.info("trash success command=%s path=%s", cmd[0], path)
                return True
            LOGGER.warning(
                "trash command failed command=%s returncode=%s stderr=%s path=%s",
                cmd[0],
                result.returncode,
                result.stderr.strip(),
                path,
            )
    return False


def move_to_macos_trash(path: Path) -> bool:
    # Finder expects a real alias. Passing "POSIX file ..." directly can fail
    # with -1728 for perfectly valid paths.
    script = (
        'on run argv\n'
        '  set targetPath to POSIX file (item 1 of argv) as alias\n'
        '  tell application "Finder" to delete targetPath\n'
        'end run'
    )
    result = subprocess.run(
        ["osascript", "-e", script, str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        LOGGER.info("trash success finder path=%s", path)
        return True

    LOGGER.warning(
        "trash finder failed returncode=%s stderr=%s path=%s",
        result.returncode,
        result.stderr.strip(),
        path,
    )
    return move_to_home_trash(path)


def move_to_home_trash(path: Path) -> bool:
    trash_dir = Path.home() / ".Trash"
    if not trash_dir.exists():
        LOGGER.warning("trash fallback unavailable missing=%s path=%s", trash_dir, path)
        return False

    destination = unique_trash_destination(trash_dir / path.name)
    try:
        shutil.move(str(path), str(destination))
        LOGGER.info("trash success fallback destination=%s path=%s", destination, path)
        return True
    except Exception:
        LOGGER.exception("trash fallback failed destination=%s path=%s", destination, path)
        return False


def unique_trash_destination(destination: Path) -> Path:
    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    parent = destination.parent
    counter = 1
    while True:
        candidate = parent / f"{stem} {counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1

def move_to_windows_recycle_bin(path: Path) -> bool:
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", wintypes.USHORT),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", wintypes.LPVOID),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    operation = SHFILEOPSTRUCTW()
    operation.hwnd = None
    operation.wFunc = 3
    operation.pFrom = str(path) + "\0\0"
    operation.pTo = None
    operation.fFlags = 0x0040 | 0x0010 | 0x0400 | 0x0004
    operation.fAnyOperationsAborted = False
    operation.hNameMappings = None
    operation.lpszProgressTitle = None

    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))
    return result == 0 and not operation.fAnyOperationsAborted
