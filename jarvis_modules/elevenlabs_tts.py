"""ElevenLabs text-to-speech integration for JARVIS."""

from __future__ import annotations

import os
from typing import Mapping, Any

import requests


DEFAULT_VOICE_ID = "HH8sIQq8WOcER3Nu118i"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"


class ElevenLabsTTSError(RuntimeError):
    pass


def api_key_from_config(cfg: Mapping[str, Any]) -> str:
    return (
        os.environ.get("ELEVENLABS_API_KEY", "").strip()
        or str(cfg.get("elevenlabs_api_key", "") or "").strip()
    )


def is_enabled(cfg: Mapping[str, Any]) -> bool:
    return bool(cfg.get("elevenlabs_enabled", True) and api_key_from_config(cfg))


def synthesize_speech(text: str, cfg: Mapping[str, Any]) -> tuple[bytes, str]:
    clean = str(text or "").strip()
    if not clean:
        raise ElevenLabsTTSError("No text provided.")

    api_key = api_key_from_config(cfg)
    if not api_key:
        raise ElevenLabsTTSError("ElevenLabs API key is not configured.")

    voice_id = str(cfg.get("elevenlabs_voice_id") or DEFAULT_VOICE_ID).strip()
    model_id = str(cfg.get("elevenlabs_model_id") or DEFAULT_MODEL_ID).strip()
    output_format = str(cfg.get("elevenlabs_output_format") or "mp3_44100_128").strip()
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format={output_format}"
    payload = {
        "text": clean[:5000],
        "model_id": model_id,
        "voice_settings": {
            "stability": float(cfg.get("elevenlabs_stability", 0.45)),
            "similarity_boost": float(cfg.get("elevenlabs_similarity_boost", 0.75)),
            "style": float(cfg.get("elevenlabs_style", 0.2)),
            "use_speaker_boost": bool(cfg.get("elevenlabs_speaker_boost", True)),
        },
    }
    headers = {
        "xi-api-key": api_key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=45)
    except Exception as exc:
        raise ElevenLabsTTSError(f"ElevenLabs request failed: {exc}") from exc

    if response.status_code >= 400:
        detail = response.text[:240].replace("\n", " ")
        raise ElevenLabsTTSError(f"ElevenLabs error {response.status_code}: {detail}")

    content_type = response.headers.get("Content-Type", "audio/mpeg").split(";")[0].strip() or "audio/mpeg"
    return response.content, content_type

