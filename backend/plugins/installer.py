"""Simple installer for local plugin files."""
import os
import shutil


def install_from_path(src_path: str, dest_dir: str | None = None) -> str:
    if dest_dir is None:
        dest_dir = os.path.dirname(__file__)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(src_path))
    shutil.copy(src_path, dest)
    return dest
