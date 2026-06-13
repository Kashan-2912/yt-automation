"""ElevenLabs text-to-speech (MP3)."""
from __future__ import annotations

import os
from pathlib import Path

import httpx

ELEVEN_BASE = "https://api.elevenlabs.io/v1"


def synthesize_to_file(
    text: str,
    out_path: Path,
    *,
    api_key: str | None = None,
    voice_id: str | None = None,
    model_id: str | None = None,
) -> None:
    api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Set ELEVENLABS_API_KEY")

    voice_id = (
        voice_id
        or os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
        or "21m00Tcm4TlvDq8ikWAM"  # Rachel — replace via env for your channel
    )
    model_id = model_id or os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    url = f"{ELEVEN_BASE}/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": float(os.environ.get("ELEVEN_STABILITY", "0.5")),
            "similarity_boost": float(os.environ.get("ELEVEN_SIMILARITY", "0.75")),
        },
    }
    headers = {
        "xi-api-key": api_key,
        "Accept": "audio/mpeg",
    }
    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        out_path.write_bytes(r.content)
