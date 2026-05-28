"""Read-only disk cleanup reporting for JARVIS."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterable


SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "AppData"}


def format_bytes(size: int) -> str:
    value = float(max(0, size))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TB"


def _safe_size(path: Path) -> int:
    try:
        return path.stat().st_size if path.is_file() else 0
    except OSError:
        return 0


def scan_folder(path: Path, max_files: int = 8000) -> tuple[int, int, list[tuple[int, Path]]]:
    total = 0
    count = 0
    largest: list[tuple[int, Path]] = []
    if not path.exists():
        return total, count, largest

    for root, dirs, files in os.walk(path):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        for file_name in files:
            file_path = Path(root) / file_name
            size = _safe_size(file_path)
            total += size
            count += 1
            if size:
                largest.append((size, file_path))
                largest.sort(reverse=True, key=lambda item: item[0])
                largest = largest[:8]
            if count >= max_files:
                return total, count, largest
    return total, count, largest


def _existing_unique(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        key = str(resolved).lower()
        if key not in seen and resolved.exists():
            seen.add(key)
            result.append(resolved)
    return result


def build_disk_cleanup_report(home: Path | None = None, extra_roots: Iterable[Path] | None = None) -> str:
    home = (home or Path.home()).expanduser().resolve()
    temp_dir = Path(tempfile.gettempdir())
    roots = [
        home / "Downloads",
        home / "Desktop",
        home / "Documents",
        home / "Pictures",
        home / "Videos",
        temp_dir,
    ]
    if extra_roots:
        roots.extend(Path(root) for root in extra_roots)

    existing = _existing_unique(roots)
    summaries: list[tuple[int, int, Path, list[tuple[int, Path]]]] = []
    biggest: list[tuple[int, Path]] = []
    for root in existing:
        total, count, largest = scan_folder(root)
        summaries.append((total, count, root, largest))
        biggest.extend(largest)

    summaries.sort(reverse=True, key=lambda item: item[0])
    biggest.sort(reverse=True, key=lambda item: item[0])
    biggest = biggest[:8]

    try:
        import psutil

        usage = psutil.disk_usage(str(home.anchor or home))
        disk_line = (
            f"Disk usage: {format_bytes(usage.used)} / {format_bytes(usage.total)} "
            f"({usage.percent:.1f}% used)."
        )
    except Exception:
        disk_line = "Disk usage: unavailable."

    lines = [disk_line, "Cleanup candidates, read-only report:"]
    if not summaries:
        lines.append("No common cleanup folders were found.")
    else:
        for total, count, root, largest in summaries[:6]:
            detail = ""
            if largest:
                detail = f"; largest {largest[0][1].name} ({format_bytes(largest[0][0])})"
            lines.append(f"- {root}: {format_bytes(total)} across {count} files{detail}")

    if biggest:
        lines.append("Largest files found:")
        for size, path in biggest[:6]:
            lines.append(f"- {format_bytes(size)}: {path}")

    lines.append("I did not delete anything. Say 'delete <path>' only after reviewing the report.")
    return "\n".join(lines)
