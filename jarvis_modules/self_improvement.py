"""Guarded self-improvement request handling for JARVIS."""

from __future__ import annotations

import datetime as _dt
import json
import re
import uuid
from pathlib import Path
from typing import Any


BLOCK_PATTERNS = {
    "covert_surveillance": re.compile(
        r"\b(?:secretly|hidden|without\s+(?:asking|telling|consent)|spy|surveil|all\s+activities)\b",
        re.I,
    ),
    "always_on_camera": re.compile(
        r"\b(?:always|24/?7|whole\s+time|all\s+the\s+time|continuously|permanent(?:ly)?)\b.*\b(?:camera|webcam|analy[sz]e\s+me|watch\s+me)\b"
        r"|\b(?:camera|webcam)\b.*\b(?:always|24/?7|whole\s+time|all\s+the\s+time|continuously|permanent(?:ly)?)\b",
        re.I,
    ),
    "security_bypass": re.compile(
        r"\b(?:disable|bypass|remove|turn\s+off)\b.*\b(?:auth|authentication|token|password|security|permission|approval)\b",
        re.I,
    ),
    "secret_access": re.compile(
        r"\b(?:read|show|send|upload|print|exfiltrate)\b.*\b(?:api[_ -]?key|token|password|secret|\.env|jarvis_config\.json)\b",
        re.I,
    ),
    "unbounded_self_modification": re.compile(
        r"\b(?:rewrite\s+yourself|modify\s+yourself|edit\s+yourself)\b.*\b(?:without\s+(?:asking|approval)|automatically|forever|unlimited)\b",
        re.I,
    ),
}

SELF_EDIT_RE = re.compile(
    r"\b(?:edit|modify|change|upgrade|improve|add|build|create|implement|update)\b.*\b(?:yourself|your code|jarvis|feature|module|ability|capability)\b"
    r"|\bself[- ]?(?:edit|improve|upgrade|modify)\b",
    re.I,
)


def looks_like_self_improvement_request(text: str) -> bool:
    return bool(SELF_EDIT_RE.search(str(text or "")))


def safety_review(text: str) -> tuple[bool, str, str]:
    """Return (allowed, category, note) for a requested self-change."""
    source = str(text or "").strip()
    for category, pattern in BLOCK_PATTERNS.items():
        if pattern.search(source):
            if category == "always_on_camera":
                return (
                    False,
                    category,
                    "Always-on camera analysis is blocked. Safer alternative: a visible, time-limited focus/health check mode with explicit start, stop, and recording-off defaults.",
                )
            if category == "covert_surveillance":
                return (
                    False,
                    category,
                    "Covert or all-activity surveillance is blocked. JARVIS can only monitor with visible consent, clear scope, and an easy stop command.",
                )
            if category == "security_bypass":
                return False, category, "Security bypass requests are blocked. Owner-only protection must stay enabled."
            if category == "secret_access":
                return False, category, "Secret-reading or secret-sharing changes are blocked."
            return False, category, "Unbounded self-modification is blocked. Changes must be scoped, logged, and testable."
    return True, "safe_request", "Request accepted for guarded implementation planning."


def _load_requests(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def save_self_improvement_request(path: str | Path, text: str, owner: str = "Prashant") -> dict[str, Any]:
    allowed, category, note = safety_review(text)
    request = {
        "id": str(uuid.uuid4()),
        "created_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "owner": owner,
        "request": str(text or "").strip(),
        "allowed": allowed,
        "category": category,
        "safety_note": note,
        "status": "queued_for_implementation" if allowed else "blocked",
        "implementation_policy": (
            "Only edit files inside the J.A.R.V.I.S workspace, preserve backups/version control, "
            "avoid secrets, run compile/tests, and keep owner-only authentication enabled."
        ),
    }
    target = Path(path)
    requests = _load_requests(target)
    requests.append(request)
    target.write_text(json.dumps(requests[-200:], indent=2, ensure_ascii=False), encoding="utf-8")
    return request


def response_for_request(request: dict[str, Any]) -> str:
    req_id = str(request.get("id", ""))[:8]
    note = str(request.get("safety_note", "")).strip()
    if request.get("allowed"):
        return (
            f"Self-improvement request queued, Prashant. ID {req_id}. "
            "Main isse guarded implementation plan ki tarah treat karunga: scoped edit, backup, tests, aur security intact. "
            f"{note}"
        )
    return (
        f"Ye self-change block kiya gaya, Prashant. ID {req_id}. "
        f"Reason: {note}"
    )
