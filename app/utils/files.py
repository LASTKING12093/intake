import os
import re
import shutil
from pathlib import Path


def sanitize_filename(title: str) -> str:
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip().rstrip(". ")
    title = title[:140].rstrip(". ") or "Untitled"
    if title.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        title = "_" + title
    return title


def publish_file(source: Path, folder: Path, title: str) -> Path:
    """Reserve destination atomically, including against other app instances."""
    folder.mkdir(parents=True, exist_ok=True)
    base = sanitize_filename(title)
    for number in range(10000):
        suffix = f" ({number})" if number else ""
        target = folder / f"{base}{suffix}{source.suffix.lower()}"
        try:
            handle = target.open("xb")
        except FileExistsError:
            continue
        try:
            with handle, source.open("rb") as incoming:
                shutil.copyfileobj(incoming, handle, 1024 * 1024)
                handle.flush()
                os.fsync(handle.fileno())
            source.unlink()
            return target
        except BaseException:
            target.unlink(missing_ok=True)
            raise
    raise OSError("Too many files with this name")
