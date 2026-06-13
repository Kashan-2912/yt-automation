#!/usr/bin/env python3
"""
Fully automated YouTube Short pipeline.

Single-variant flow:
  Groq → narration + image prompts
  Edge TTS → audio (30-40s)
  DeAPI → images
  Captions → SRT
  FFmpeg → 9:16 vertical MP4
  YouTube upload (optional)

Bilingual flow (preset has `variants`):
  Groq → image_prompts + per-language {title, description, narration}
  DeAPI → images (once, shared)
  For each variant:
    Edge TTS → audio in that language with that voice
    Captions → SRT
    FFmpeg → MP4 with variant-specific font
    YouTube upload (optional, per-channel token)

Usage:
  .venv/bin/python scripts/run_short.py --channel ghost_stories
  .venv/bin/python scripts/run_short.py --channel facts --upload --privacy public
  .venv/bin/python scripts/run_short.py --channel hindi_myth
  # hindi_myth: topic = IST day theme (Ganesha→Shiva→…) + random unused line; --topic overrides
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "scripts" / ".env")

from pipeline.captions import build_srt
from pipeline.channel_presets import get_preset, list_channel_ids
from pipeline.edge_tts_synth import synthesize_full
from pipeline.groq_script import generate_short_pack
from pipeline.images import DEFAULT_NEGATIVE, full_visual_prompt, save_scene_image
from pipeline.render_short import render_vertical_short
from pipeline.story_history import save_title


def _render_and_upload(
    *,
    variant_label: str,
    narration: str,
    title: str,
    description: str,
    voice: str | None,
    font_file: str,
    font_name: str,
    image_paths: list,
    run_dir: Path,
    suffix: str,
    upload: bool,
    privacy: str,
    yt_token_env: str = "YT_REFRESH_TOKEN",
) -> Path:
    """Render one video (audio + SRT + MP4) for a single variant. Optionally upload."""
    print(f"\n━━━ Variant: {variant_label} ━━━")

    audio_path = run_dir / f"voiceover{suffix}.mp3"
    print(f"② Edge TTS ({voice or 'default'})…")
    total_dur, sentence_timings = synthesize_full(narration, audio_path, voice=voice)
    print(f"   Audio: {total_dur:.1f}s ({len(sentence_timings)} sentences tracked)")
    if total_dur > 55:
        print(f"   ⚠ Audio is {total_dur:.0f}s — target is 30-45s")
    if total_dur < 25:
        print(f"   ⚠ Audio is {total_dur:.0f}s — might be too short")

    srt_path = run_dir / f"captions{suffix}.srt"
    print("④ Captions…")
    build_srt(sentence_timings, srt_path, total_dur)

    video_path = run_dir / f"short{suffix}.mp4"
    print(f"⑤ FFmpeg: rendering 1080×1920 (font={font_name})…")
    render_vertical_short(
        image_paths, total_dur, audio_path, srt_path, video_path,
        font_file=font_file, font_name=font_name,
    )
    print(f"   → {video_path}")

    if upload:
        from pipeline.youtube_upload import upload_short
        print(f"⑥ YouTube: uploading ({yt_token_env})…")
        vid = upload_short(
            video_path, title, description,
            privacy_status=privacy,
            refresh_token_env=yt_token_env,
        )
        print(f"   Uploaded! https://www.youtube.com/shorts/{vid}")
    else:
        print("   (skip upload — pass --upload)")

    return video_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate & optionally upload a YouTube Short.")
    ap.add_argument("--channel", required=True, choices=list_channel_ids())
    ap.add_argument("--topic", default="", help="Optional topic hint for Groq.")
    ap.add_argument("--upload", action="store_true", help="Upload to YouTube after render.")
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    args = ap.parse_args()

    preset = get_preset(args.channel)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = REPO_ROOT / "output" / "runs" / f"{args.channel}_{ts}"
    img_dir = run_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    # Myth rotation: IST calendar picks theme (Ganesha → Shiva → …); random unused topic in that theme.
    myth_theme_for_commit: str | None = None
    myth_topic_for_commit: str | None = None

    # Pick a topic: CLI --topic wins; else myth rotation; else random from topic_pool.
    topic_hint = args.topic.strip() or None
    if not topic_hint:
        if preset.get("topic_rotation") == "myth":
            from pipeline.myth_topics import pick_myth_topic

            topic_hint, myth_theme_for_commit = pick_myth_topic(args.channel)
            myth_topic_for_commit = topic_hint
            print(f"📿 Myth theme today (IST): {myth_theme_for_commit} → {topic_hint!r}")
        else:
            pool = preset.get("topic_pool") or []
            if pool:
                topic_hint = random.choice(pool)
                print(f"🎲 Random topic from pool: {topic_hint!r}")

    variants = preset.get("variants") or []
    primary_video_path: Path | None = None

    # ── 1. Script via Groq ───────────────────────────────────────────
    print("① Groq: generating script…")
    pack = generate_short_pack(
        preset, topic_hint=topic_hint, channel_id=args.channel,
    )
    (run_dir / "script.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")

    image_prompts = pack["image_prompts"]

    if variants:
        # Bilingual mode: each lang gets its own audio/SRT/video
        first_v = variants[0]
        first_node = pack["variants"][first_v["lang"]]
        print(f"   Title ({first_v['label']}): {first_node['youtube_title']}")
        for v in variants:
            node = pack["variants"][v["lang"]]
            wc = len(node["full_narration"].split())
            print(f"   {v['label']}: {wc} words")
        print(f"   {len(image_prompts)} image prompts (shared)")
        history_title = first_node["youtube_title"]
        history_narration = first_node["full_narration"]
    else:
        title = pack["youtube_title"]
        narration = pack["full_narration"]
        word_count = len(narration.split())
        print(f"   Title: {title}")
        print(f"   Narration: {word_count} words, {len(image_prompts)} image prompts")
        history_title = title
        history_narration = narration

    # ── 2. Images via DeAPI (generated ONCE, shared by all variants) ──
    w = int(os.environ.get("DEAPI_IMAGE_WIDTH", "768"))
    h = int(os.environ.get("DEAPI_IMAGE_HEIGHT", "768"))
    style_suffix = preset.get("image_style_suffix")
    negative = (
        os.environ.get("IMAGE_NEGATIVE_PROMPT")
        or preset.get("image_negative_prompt")
        or DEFAULT_NEGATIVE
    )
    cooldown = int(os.environ.get("DEAPI_COOLDOWN", "10"))

    print(f"③ Images: {len(image_prompts)} scenes ({cooldown}s cooldown)…")
    image_paths: list[Path] = []
    for i, ip in enumerate(image_prompts):
        prompt = full_visual_prompt(ip, style_suffix=style_suffix)
        out = img_dir / f"scene_{i + 1:02d}.png"
        st, detail = save_scene_image(i + 1, prompt, out, width=w, height=h, negative=negative)
        if st != "ok":
            raise RuntimeError(f"Image {i + 1} failed: {detail}")
        print(f"   scene {i + 1}/{len(image_prompts)}: {detail}")
        image_paths.append(out)
        if i < len(image_prompts) - 1:
            time.sleep(cooldown)

    # ── 4-6. Render (per variant) ────────────────────────────────────
    if variants:
        for v in variants:
            node = pack["variants"][v["lang"]]
            _render_and_upload(
                variant_label=v["label"],
                narration=node["full_narration"],
                title=node["youtube_title"],
                description=node.get("youtube_description", ""),
                voice=v.get("tts_voice"),
                font_file=v.get("caption_font", "CreepsterCaps.ttf"),
                font_name=v.get("caption_font_name", "Creepster"),
                image_paths=image_paths,
                run_dir=run_dir,
                suffix=f"_{v['lang']}",
                upload=args.upload,
                privacy=args.privacy,
                yt_token_env=v.get("yt_token_env", "YT_REFRESH_TOKEN"),
            )
    else:
        primary_video_path = _render_and_upload(
            variant_label=preset.get("language", "en"),
            narration=narration,
            title=title,
            description=pack.get("youtube_description", ""),
            voice=preset.get("tts_voice") or os.environ.get("EDGE_TTS_VOICE"),
            font_file=preset.get("caption_font", "CreepsterCaps.ttf"),
            font_name=preset.get("caption_font_name", "Creepster"),
            image_paths=image_paths,
            run_dir=run_dir,
            suffix="",
            upload=args.upload,
            privacy=args.privacy,
            yt_token_env=preset.get("yt_token_env") or "YT_REFRESH_TOKEN",
        )

    # ── 7. History ───────────────────────────────────────────────────
    summary = " ".join(history_narration.split()[:25]) + "…"
    save_title(args.channel, history_title, summary)

    if myth_theme_for_commit and myth_topic_for_commit:
        from pipeline.myth_topics import commit_myth_topic

        commit_myth_topic(args.channel, myth_theme_for_commit, myth_topic_for_commit)

    # Optional second upload: same rendered MP4 to extra channels (e.g. second bhakti channel).
    # Uses env var names listed in preset["extra_yt_token_envs"].
    extra_envs = preset.get("extra_yt_token_envs") or []
    if args.upload and primary_video_path and extra_envs:
        from pipeline.youtube_upload import upload_short

        for env_name in extra_envs:
            print(f"⑦ Extra YouTube upload ({env_name})…")
            vid_extra = upload_short(
                primary_video_path,
                history_title,
                pack.get("youtube_description", ""),
                privacy_status=args.privacy,
                refresh_token_env=env_name,
            )
            print(f"   Extra channel video: https://www.youtube.com/shorts/{vid_extra}")

    print("\n✓ Done.")


if __name__ == "__main__":
    main()
