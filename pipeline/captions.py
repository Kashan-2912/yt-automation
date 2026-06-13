"""Build SRT captions from Edge TTS sentence-level timestamps.

Splits each sentence into word groups (~6-8 words) and distributes
timing proportionally within the sentence's known time window.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.edge_tts_synth import SentenceTiming


def _fmt(ms: int) -> str:
    """Milliseconds -> SRT timestamp."""
    h = ms // 3_600_000
    m = (ms % 3_600_000) // 60_000
    s = (ms % 60_000) // 1_000
    frac = ms % 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{frac:03d}"


def build_srt(
    sentences: list[SentenceTiming],
    out_path: Path,
    total_duration: float,
    *,
    max_words_per_line: int = 5,
) -> Path:
    """Create .srt from sentence timestamps, splitting long sentences."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not sentences:
        out_path.write_text("", encoding="utf-8")
        return out_path

    chunks: list[tuple[int, int, str]] = []

    for sent in sentences:
        words = sent["text"].split()
        if not words:
            continue

        start_ms = sent["offset_ms"]
        dur_ms = sent["duration_ms"]

        if len(words) <= max_words_per_line:
            chunks.append((start_ms, start_ms + dur_ms, sent["text"]))
        else:
            n_groups = (len(words) + max_words_per_line - 1) // max_words_per_line
            ms_per_word = dur_ms / len(words) if words else 1

            pos = 0
            for g in range(n_groups):
                grp_start = pos
                grp_end = min(pos + max_words_per_line, len(words))
                grp_text = " ".join(words[grp_start:grp_end])

                t_start = start_ms + int(grp_start * ms_per_word)
                t_end = start_ms + int(grp_end * ms_per_word)
                t_end = min(t_end, start_ms + dur_ms)

                chunks.append((t_start, t_end, grp_text))
                pos = grp_end

    lines: list[str] = []
    for i, (start, end, text) in enumerate(chunks):
        lines.append(str(i + 1))
        lines.append(f"{_fmt(start)} --> {_fmt(end)}")
        lines.append(text)
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
