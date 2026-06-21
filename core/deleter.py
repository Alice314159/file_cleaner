import shutil
import subprocess
import sys
from pathlib import Path


def delete_item(path: str) -> bool:
    try:
        p = Path(path)
        if not p.exists():
            return False
        return move_to_trash(p)
    except Exception:
        return False


def move_to_trash(path: Path) -> bool:
    if sys.platform == "darwin":
        script = (
            'on run argv\n'
            '  tell application "Finder" to delete POSIX file (item 1 of argv)\n'
            'end run'
        )
        result = subprocess.run(
            ["osascript", "-e", script, str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0

    if sys.platform == "win32":
        return move_to_windows_recycle_bin(path)

    for cmd in (["gio", "trash", str(path)], ["trash-put", str(path)]):
        if shutil.which(cmd[0]):
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode == 0:
                return True
    return False


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
