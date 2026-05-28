"""Safe self-knowledge indexing for the JARVIS project."""

from __future__ import annotations

import ast
import datetime as _dt
import json
import os
import re
from pathlib import Path
from typing import Any


SKIP_DIR_NAMES = {
    ".git",
    ".jarvis_runtime",
    ".pytest_cache",
    ".venv",
    ".buildozer",
    ".buildozer-venv",
    "__pycache__",
    "build",
    "dist",
    "jarvis_generated",
    "jarvis_photos",
    "jarvisphotos",
    "node_modules",
    "owner_faces",
    "site-packages",
    "uploads",
    "vosk-model-small-en-us-0.15",
}

SKIP_FILE_NAMES = {
    ".env",
    "jarvis_config.json",
    "jarvis_ai_history.json",
    "jarvis_ai_memory.json",
}

SKIP_NAME_PARTS = {
    "api_key",
    "apikey",
    "credential",
    "password",
    "secret",
    "session",
    "token",
}

TEXT_EXTENSIONS = {
    ".bat",
    ".cfg",
    ".css",
    ".csv",
    ".dockerignore",
    ".env.example",
    ".gitignore",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".spec",
    ".toml",
    ".ts",
    ".txt",
    ".yml",
    ".yaml",
}

MAX_TEXT_BYTES = 256 * 1024
MAX_ENTRIES = 2000


def _is_sensitive(path: Path) -> bool:
    lower_name = path.name.lower()
    if lower_name in SKIP_FILE_NAMES:
        return True
    normalized = re.sub(r"[^a-z0-9]+", "", str(path).lower())
    if "apikey" in normalized:
        return True
    tokens: set[str] = set()
    for part in path.parts:
        tokens.update(token for token in re.split(r"[^a-z0-9]+", part.lower()) if token)
    return any(part in tokens for part in SKIP_NAME_PARTS)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _python_summary(path: Path, text: str) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "python"}
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return result

    doc = ast.get_docstring(tree)
    if doc:
        result["purpose"] = " ".join(doc.split())[:240]

    classes: list[str] = []
    functions: list[str] = []
    imports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module.split(".")[0])

    if classes:
        result["classes"] = classes[:20]
    if functions:
        result["functions"] = functions[:30]
    if imports:
        result["imports"] = sorted(set(imports))[:25]
    return result


def _text_summary(path: Path, text: str) -> dict[str, Any]:
    suffix = path.suffix.lower()
    result: dict[str, Any] = {"type": suffix.lstrip(".") or "text"}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if path.name.lower() == "dockerfile":
        result["type"] = "dockerfile"
    if suffix in {".md", ".txt"} and lines:
        title = next((line.lstrip("# ").strip() for line in lines if line.startswith("#")), lines[0])
        result["purpose"] = title[:240]
    elif suffix in {".json", ".yml", ".yaml", ".toml"} and lines:
        result["purpose"] = "Configuration or structured data file."
    elif lines:
        result["purpose"] = lines[0][:240]
    return result


def _file_entry(root: Path, path: Path) -> dict[str, Any]:
    rel = path.relative_to(root).as_posix()
    stat = path.stat()
    entry: dict[str, Any] = {
        "path": rel,
        "size_bytes": stat.st_size,
        "modified": _dt.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
    }
    suffix = path.suffix.lower()
    if suffix not in TEXT_EXTENSIONS and path.name.lower() != "dockerfile":
        entry["type"] = "non_text"
        return entry
    if stat.st_size > MAX_TEXT_BYTES:
        entry["type"] = "large_text"
        entry["purpose"] = "Text file too large for detailed self-indexing."
        return entry

    text = _read_text(path)
    entry["line_count"] = text.count("\n") + (1 if text else 0)
    if suffix == ".py":
        entry.update(_python_summary(path, text))
    else:
        entry.update(_text_summary(path, text))
    return entry


def build_self_knowledge(root: str | Path, output_file: str | Path | None = None) -> dict[str, Any]:
    """Create a safe, bounded map of the JARVIS codebase without reading secrets."""
    project_root = Path(root).resolve()
    generated_at = _dt.datetime.now().isoformat(timespec="seconds")
    entries: list[dict[str, Any]] = []
    skipped = {"directories": 0, "sensitive_files": 0, "non_text_or_large_files": 0, "entry_limit": 0}
    visited_files = 0
    directory_names: set[str] = set()

    for current, dirs, files in os.walk(project_root):
        blocked_dirs = [d for d in dirs if d in SKIP_DIR_NAMES]
        skipped["directories"] += len(blocked_dirs)
        dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]
        rel_dir = Path(current).relative_to(project_root).as_posix()
        if rel_dir != ".":
            directory_names.add(rel_dir)

        for file_name in sorted(files):
            path = Path(current) / file_name
            visited_files += 1
            if _is_sensitive(path):
                skipped["sensitive_files"] += 1
                continue
            if len(entries) >= MAX_ENTRIES:
                skipped["entry_limit"] += 1
                continue
            try:
                entry = _file_entry(project_root, path)
            except OSError:
                skipped["non_text_or_large_files"] += 1
                continue
            if entry.get("type") in {"non_text", "large_text"}:
                skipped["non_text_or_large_files"] += 1
            entries.append(entry)

    python_files = [e for e in entries if e.get("type") == "python"]
    module_files = [e["path"] for e in python_files[:40]]
    classes = sorted({c for e in python_files for c in e.get("classes", [])})
    important_docs = [e["path"] for e in entries if Path(e["path"]).suffix.lower() in {".md", ".txt"}][:25]

    summary_lines = [
        "I am JARVIS, a Python-based personal assistant project built for Prashant.",
        "My main runtime is jarvis.py, with reusable helpers under jarvis_modules and tests under backend/tests.",
        "I am made from voice input/output, AI chat and vision, Windows system control, camera, email, weather, news, notes, calendar, browser/automation, WhatsApp, Telegram, contacts, owner-face recognition, proactive prompts, and web/backend bridge pieces.",
        f"This self-index saw {visited_files} files and recorded {len(entries)} safe entries while skipping secrets, sessions, caches, virtual environments, binaries, and large assets.",
    ]
    if classes:
        summary_lines.append("Key classes I found include: " + ", ".join(classes[:35]) + ".")
    if module_files:
        summary_lines.append("Important code files include: " + ", ".join(module_files[:25]) + ".")

    data: dict[str, Any] = {
        "generated_at": generated_at,
        "project_root": str(project_root),
        "summary": "\n".join(summary_lines),
        "directories": sorted(directory_names)[:200],
        "important_docs": important_docs,
        "entries": entries,
        "skipped": skipped,
    }

    if output_file:
        out = Path(output_file)
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def load_self_knowledge(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        return {}
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def compact_self_knowledge_text(path: str | Path, max_chars: int = 5000) -> str:
    data = load_self_knowledge(path)
    if not data:
        return ""
    parts = [
        f"Generated at: {data.get('generated_at', 'unknown')}",
        str(data.get("summary", "")).strip(),
    ]
    docs = data.get("important_docs") or []
    if docs:
        parts.append("Docs: " + ", ".join(str(item) for item in docs[:12]))
    entries = data.get("entries") or []
    code_bits = []
    for entry in entries:
        if entry.get("type") != "python":
            continue
        names = []
        if entry.get("classes"):
            names.append("classes " + ", ".join(entry["classes"][:6]))
        if entry.get("functions"):
            names.append("functions " + ", ".join(entry["functions"][:8]))
        if names:
            code_bits.append(f"{entry.get('path')}: {'; '.join(names)}")
        if len(code_bits) >= 20:
            break
    if code_bits:
        parts.append("Code map:\n" + "\n".join(code_bits))
    text = "\n\n".join(part for part in parts if part)
    if len(text) > max_chars:
        return text[:max_chars].rstrip() + "\n...[truncated]"
    return text
