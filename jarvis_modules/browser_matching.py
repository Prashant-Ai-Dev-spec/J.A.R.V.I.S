"""Fuzzy matching helpers for browser automation commands."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable, Mapping, Any


_SYNONYMS = {
    "information": {"learn", "more", "details", "info", "about"},
    "info": {"learn", "more", "details", "information", "about"},
    "details": {"learn", "more", "information", "info", "about"},
    "login": {"sign", "in", "signin", "log"},
    "signin": {"sign", "in", "login", "log"},
    "signup": {"sign", "up", "register", "join"},
    "register": {"sign", "up", "signup", "join"},
    "search": {"find", "lookup", "go"},
}


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _words(value: str) -> set[str]:
    return {word for word in normalize_text(value).split() if word}


def score_text_match(label: str, candidate: str) -> float:
    label_norm = normalize_text(label)
    candidate_norm = normalize_text(candidate)
    if not label_norm or not candidate_norm:
        return 0.0

    score = SequenceMatcher(None, label_norm, candidate_norm).ratio()
    label_words = _words(label_norm)
    candidate_words = _words(candidate_norm)

    if label_norm in candidate_norm or candidate_norm in label_norm:
        score += 0.35
    shared = label_words & candidate_words
    if shared:
        score += min(0.35, 0.12 * len(shared))

    for word in label_words:
        if _SYNONYMS.get(word, set()) & candidate_words:
            score += 0.28

    if len(candidate_norm) <= 36:
        score += 0.05

    return score


def best_text_match(label: str, candidates: Iterable[Mapping[str, Any]], minimum: float = 0.42) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_score = 0.0
    for candidate in candidates:
        text = str(candidate.get("text") or candidate.get("label") or "").strip()
        score = score_text_match(label, text)
        if score > best_score:
            best_score = score
            best = dict(candidate)
            best["score"] = score
    if best and best_score >= minimum:
        return best
    return None

