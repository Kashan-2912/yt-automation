"""Track past stories so Groq never repeats plot, setting, or characters.

Stores title + short summary in output/history/<channel>.json.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HISTORY_DIR = REPO_ROOT / "output" / "history"
MAX_HISTORY = 200


def _history_path(channel: str) -> Path:
    return HISTORY_DIR / f"{channel}.json"


def load_history(channel: str) -> list[dict]:
    p = _history_path(channel)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            normalized = []
            for item in data:
                if isinstance(item, str):
                    normalized.append({"title": item, "summary": ""})
                elif isinstance(item, dict):
                    normalized.append(item)
            return normalized
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_title(channel: str, title: str, summary: str = "") -> None:
    history = load_history(channel)
    history.append({"title": title.strip(), "summary": summary.strip()})
    history = history[-MAX_HISTORY:]
    p = _history_path(channel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def history_prompt_block(channel: str) -> str:
    """Returns a string to inject into the Groq prompt, or empty if no history."""
    history = load_history(channel)
    if not history:
        return ""
    recent = history[-50:]
    lines = []
    for entry in recent:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        if summary:
            lines.append(f"  - \"{title}\" — {summary}")
        else:
            lines.append(f"  - \"{title}\"")

    listing = "\n".join(lines)
    return (
        "\n\nIMPORTANT — Do NOT repeat or closely resemble any of these past stories. "
        "Pick a COMPLETELY different plot, setting, characters, and theme:\n"
        f"{listing}\n"
    )
