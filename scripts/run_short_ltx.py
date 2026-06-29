#!/usr/bin/env python3
"""
Fully automated LTX-2.3 22B Text-to-Video YouTube Short pipeline.

Generates:
  Groq → narration + 8 video prompts
  Edge TTS → audio voiceover
  DeAPI → 8 video clips via LTX-2.3 22B txt2video API
  Captions → SRT
  FFmpeg → pre-process, time-scale, xfade stitch and overlay captions
  YouTube upload (optional)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Force UTF-8 output so Unicode/emoji prints work on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "scripts" / ".env")

from pipeline.captions import build_srt
from pipeline.channel_presets import get_preset, list_channel_ids
from pipeline.edge_tts_synth import synthesize_full
from pipeline.groq_script import generate_short_pack
from pipeline.story_history import save_title

# Configured DeAPI Tokens (Primary from .env + fallback pools)
DEAPI_TOKENS = [
    os.environ.get("DEAPI_TOKEN", "").strip(),
    # "vvQBZjPmi2NFQIfFpgl0Tg0F0bL3Q089zEuCBDwpdf592e0e",
    # "CmoqMsdDCOMqyk2p5EWBuIEqGlIXnDXhzw0Qdi3if98d2c68",
    # "cHwRcpd9Y5C5exKKn8JtV0z6KCmGJXmjirwr7fNS9d853eaa",
    # "kLc4wC1jBvD0y3crCyy5UWTE3F6i5CR9nZ4s2vd6956df81d",
    # "iSWCv39zIWMpyMlIB8LirMcOEuW3JvzNivgQapxLc7243c98",
    # "GplQ0cRbQCKnOVd7efJoOk0YlyoqmXZjEziQCrBQba2fdcc3",
    "JSZOJagE5gIUgmOqqnO4EBfpvth8KHpJnkE4Kd7Ye128da12",
    "cjdMSPDhe4cOyfWcZQcHvAQXHYadGZj4h2565Uvrf4610980",
    "XoVcUBLInf58Jk4GKB8sp0oOyq6SQywo2978gQlgdbfed35d",
    "XitC4DlDWS9flLDqO2xiDSMBFX0kFKwJsiFRPNyb6f1533d2",
]
DEAPI_TOKENS = [t for t in DEAPI_TOKENS if t]
current_token_idx = 0

SUBMIT_URL  = "https://api.deapi.ai/api/v1/client/txt2video"
POLL_URL    = "https://api.deapi.ai/api/v1/client/request-status"
MODEL_SLUG  = "Ltx2_3_22B_Dist_INT8"

# 9:16 vertical parameters for LTX model
WIDTH   = 576
HEIGHT  = 1024
FPS     = 24
FRAMES  = 97    # ~4.04 seconds

MIN_CLIPS = 4   # minimum clips to proceed with rendering
FADE_DUR = 0.45
TRANSITIONS = [
    "dissolve",
    "fade",
    "slideleft",
    "slideright",
    "slideup",
    "wipeleft",
    "wiperight",
    "smoothleft",
    "smoothright",
]


def get_current_token() -> str:
    global current_token_idx
    if not DEAPI_TOKENS:
        raise RuntimeError("No DeAPI tokens configured!")
    return DEAPI_TOKENS[current_token_idx % len(DEAPI_TOKENS)]


def get_token_preview(token: str) -> str:
    if len(token) > 8:
        return f"{token[:4]}...{token[-4:]}"
    return token


def submit_video(prompt: str, client: httpx.Client) -> tuple[str, str]:
    """Submit a txt2video job. Rotates token on rate limit, credit, or 422 errors."""
    global current_token_idx
    payload = {
        "prompt": prompt,
        "model": MODEL_SLUG,
        "width": WIDTH,
        "height": HEIGHT,
        "fps": FPS,
        "frames": FRAMES,
        "seed": random.randint(1, 2147483647),
    }

    max_rotation_attempts = len(DEAPI_TOKENS) * 2

    for attempt in range(max_rotation_attempts):
        token = get_current_token()
        preview = get_token_preview(token)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        print(f"      Submitting via token: {preview}")

        try:
            resp = client.post(SUBMIT_URL, json=payload, headers=headers, timeout=60.0)

            # Treat 422/400/402 as rotatable — often means credit exhaustion
            # even when the error body doesn't contain standard keywords
            if resp.status_code in (400, 402, 422):
                print(f"      [{resp.status_code} Error] Token {preview}: {resp.text[:200]}")
                print(f"      Rotating to next token...")
                current_token_idx += 1
                time.sleep(2)
                continue

            if resp.status_code == 429:
                print(f"      Token {preview} hit rate limit. Rotating to next token...")
                current_token_idx += 1
                time.sleep(2)
                continue

            resp.raise_for_status()
            data = resp.json()
            request_id = data.get("data", {}).get("request_id")
            if not request_id:
                raise RuntimeError(f"No request_id in response: {data}")
            return request_id, token

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status in (401, 403):
                print(f"      [Auth Error {status}] Token {preview} unauthorized/invalid. Rotating...")
                current_token_idx += 1
                time.sleep(2)
                continue
            else:
                raise
        except httpx.RequestError as e:
            print(f"      [Network Error] {e}. Retrying submission in 5s...")
            time.sleep(5)
            continue

    raise RuntimeError("All configured DeAPI tokens are exhausted, unauthorized, or rate-limited!")


def poll_video(request_id: str, token: str, client: httpx.Client, max_polls: int = 150) -> bytes:
    """Poll until video is ready. Uses the token that successfully submitted the job."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    
    for attempt in range(1, max_polls + 1):
        try:
            resp = client.get(f"{POLL_URL}/{request_id}", headers=headers, timeout=30.0)
            
            if resp.status_code == 429:
                print(f"      [429 Status] Rate limited on polling status — waiting 15s...")
                time.sleep(15)
                continue
                
            resp.raise_for_status()
            data = resp.json().get("data", {})
            status = data.get("status", "")

            print(f"   Poll {attempt}: status={status}")

            if status in ("completed", "success", "done"):
                video_url = data.get("result_url")
                if not video_url:
                    raise RuntimeError(f"Done but no result_url: {data}")
                vid_resp = client.get(video_url, timeout=120.0)
                vid_resp.raise_for_status()
                return vid_resp.content

            if status in ("failed", "error"):
                raise RuntimeError(f"Job failed: {data}")

            time.sleep(5)

        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            print(f"      [Poll Warning] Error checking status: {e}. Retrying in 10s...")
            time.sleep(10)

    raise RuntimeError(f"Timed out after {max_polls} polls")


def get_video_duration(path: Path) -> float:
    """Read video duration using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        # Default fallback for 97 frames at 24fps
        return 4.04167


def preprocess_clip(src: Path, dst: Path, target_dur: float) -> None:
    """Scale, crop to 1080x1920, and change speed (setpts) to match target duration at 30fps."""
    orig_dur = get_video_duration(src)
    vf = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,"
        f"setpts=PTS*({target_dur}/{orig_dur}),"
        f"fps=30"
    )
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(src),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "15",
        str(dst)
    ]
    subprocess.run(cmd, check=True)


def render_video_ltx(
    clips: list[Path],
    audio_path: Path,
    srt_path: Path,
    out_video: Path,
    total_dur: float,
    tmp_dir: Path,
    font_file: str,
    font_name: str,
) -> None:
    """Concatenate 8 preprocessed clips with transitions and captions overlay."""
    shutil.copyfile(srt_path, tmp_dir / "captions.srt")
    
    # Font setup
    fonts_dir = REPO_ROOT / "assets" / "fonts"
    font_path = fonts_dir / font_file
    rendered_font_name = "Arial"
    fontsdir_arg = ""
    if font_path.is_file():
        font_subdir = tmp_dir / "_fonts"
        font_subdir.mkdir(exist_ok=True)
        shutil.copyfile(font_path, font_subdir / font_path.name)
        rendered_font_name = font_name
        fontsdir_arg = ":fontsdir='_fonts'"
    
    force_style = (
        f"FontName={rendered_font_name},"
        f"FontSize=20,"
        f"PrimaryColour=&H00FFFFFF,"
        f"OutlineColour=&H00000000,"
        f"BackColour=&HA0000000,"
        f"BorderStyle=4,Outline=2,Bold=1,"
        f"Shadow=0,Alignment=2,"
        f"MarginV=40,MarginL=30,MarginR=30"
    )

    # Copy files locally to avoid complex escaping
    rel_clips = []
    for i, clip in enumerate(clips):
        rel_name = f"proc_clip_{i+1:02d}.mp4"
        shutil.copyfile(clip, tmp_dir / rel_name)
        rel_clips.append(rel_name)
    
    rel_audio = "voiceover.mp3"
    shutil.copyfile(audio_path, tmp_dir / rel_audio)

    n = len(clips)
    clip_dur = (total_dur + (n - 1) * FADE_DUR) / n if n > 1 else total_dur
    
    transition = random.choice(TRANSITIONS)
    print(f"   Stitch: Using transition style {transition!r}")

    inputs = []
    for rc in rel_clips:
        inputs += ["-i", rc]
    inputs += ["-i", rel_audio]

    filter_parts = []
    if n == 1:
        filter_parts.append(
            f"[0:v]subtitles=captions.srt{fontsdir_arg}:"
            f"force_style='{force_style}'[final]"
        )
    else:
        prev = "[0:v]"
        for i in range(n - 1):
            offset = (i + 1) * (clip_dur - FADE_DUR)
            next_v = f"[{i + 1}:v]"
            out = f"[x{i}]"
            filter_parts.append(
                f"{prev}{next_v}xfade=transition={transition}:"
                f"duration={FADE_DUR:.4f}:offset={offset:.4f}{out}"
            )
            prev = out
        filter_parts.append(
            f"{prev}subtitles=captions.srt{fontsdir_arg}:"
            f"force_style='{force_style}'[final]"
        )

    fc = ";\n".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        *inputs,
        "-filter_complex", fc,
        "-map", "[final]", "-map", f"{n}:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(out_video.resolve()),
    ]
    subprocess.run(cmd, check=True, cwd=str(tmp_dir))


def main() -> None:
    if not DEAPI_TOKENS:
        print("ERROR: No DeAPI tokens configured in script or .env")
        sys.exit(1)

    ap = argparse.ArgumentParser(description="Generate LTX video-based YouTube Short.")
    ap.add_argument("--channel", default="fifa_2026", choices=list_channel_ids())
    ap.add_argument("--topic", default="", help="Optional topic hint for Groq.")
    ap.add_argument("--upload", action="store_true", help="Upload to YouTube after render.")
    ap.add_argument("--instagram", action="store_true", help="Upload to Instagram Reels after render.")
    ap.add_argument("--facebook", action="store_true", help="Upload to Facebook Page Reels after render.")
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    args = ap.parse_args()

    # Get preset and override segment_count to 8 for video scenes
    preset = get_preset(args.channel)
    preset = dict(preset)
    preset["segment_count"] = 8
    preset["min_words"] = 90

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = REPO_ROOT / "output" / "runs" / f"{args.channel}_ltx_{ts}"
    vid_dir = run_dir / "videos"
    tmp_dir = run_dir / "temp"
    
    vid_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Groq Script Generation
    topic_hint = args.topic.strip() or None
    fifa_context = None
    if not topic_hint and preset.get("topic_rotation") == "fifa_2026":
        from pipeline.fifa_2026 import pick_fifa_topic
        topic_hint, fifa_context = pick_fifa_topic()
        print(f"[FIFA 2026] Content angle selected: {topic_hint!r}")

    print("\n① Groq: generating script with 8 segments...")
    pack = generate_short_pack(
        preset, topic_hint=topic_hint, channel_id=args.channel,
        extra_context=fifa_context,
    )
    (run_dir / "script.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")

    title = pack["youtube_title"]
    narration = pack["full_narration"]
    video_prompts = pack["image_prompts"] # generated from segment_count=8

    print(f"   Title: {title}")
    print(f"   Narration: {len(narration.split())} words")
    print(f"   Video prompts generated: {len(video_prompts)}")

    # 2. Synthesize TTS
    audio_path = run_dir / "voiceover.mp3"
    voice = preset.get("tts_voice") or os.environ.get("EDGE_TTS_VOICE")
    print(f"\n② Edge TTS ({voice or 'default'})...")
    total_dur, sentence_timings = synthesize_full(narration, audio_path, voice=voice)
    print(f"   Audio: {total_dur:.1f}s ({len(sentence_timings)} sentences)")

    # 3. Create captions SRT
    srt_path = run_dir / "captions.srt"
    print("\n③ Captions (SRT)...")
    build_srt(sentence_timings, srt_path, total_dur)

    # 4. Generate 8 Videos via DeAPI txt2video
    cooldown = 10
    n_prompts = len(video_prompts)
    print(f"\n④ DeAPI Video Generation: {n_prompts} clips ({cooldown}s cooldown between submissions)...")
    raw_video_paths = []
    
    with httpx.Client(timeout=120.0) as client:
        for i, prompt in enumerate(video_prompts, 1):
            full_prompt = prompt + (preset.get("image_style_suffix") or "")
            print(f"   [Clip {i}/{n_prompts}] Submitting prompt: {full_prompt[:80]}...")
            
            clip_ok = False
            for clip_attempt in range(3):  # up to 3 attempts per clip
                try:
                    if clip_attempt > 0:
                        print(f"      [Retry {clip_attempt}/2] Re-attempting clip {i}...")
                        time.sleep(5)
                    request_id, successful_token = submit_video(full_prompt, client)
                    print(f"      Job ID: {request_id}")
                    
                    video_bytes = poll_video(request_id, successful_token, client)
                    
                    clip_path = vid_dir / f"raw_clip_{i:02d}.mp4"
                    clip_path.write_bytes(video_bytes)
                    print(f"      Saved raw clip to: {clip_path} ({len(video_bytes)//1024}KB)")
                    raw_video_paths.append(clip_path)
                    clip_ok = True
                    break
                except Exception as e:
                    print(f"      [Clip {i} Error] Attempt {clip_attempt + 1}/3 failed: {e}")
            
            if not clip_ok:
                print(f"      ⚠ Clip {i} SKIPPED after 3 failed attempts")

            if i < n_prompts:
                print(f"      Waiting {cooldown}s cooldown...")
                time.sleep(cooldown)

    n_clips = len(raw_video_paths)
    if n_clips < MIN_CLIPS:
        raise RuntimeError(
            f"Only {n_clips}/{n_prompts} clips generated — need at least {MIN_CLIPS}. "
            f"All DeAPI tokens may be exhausted."
        )
    if n_clips < n_prompts:
        print(f"\n   ⚠ Continuing with {n_clips}/{n_prompts} clips (minimum {MIN_CLIPS} met)")

    # 5. Pre-process and time-scale clips
    print("\n⑤ Pre-processing clips (scaling, cropping to 1080x1920, and adjusting speed)...")
    clip_dur = (total_dur + (n_clips - 1) * FADE_DUR) / n_clips
    print(f"   Target duration per clip: {clip_dur:.2f}s ({n_clips} clips)")
    
    processed_video_paths = []
    for i, raw_path in enumerate(raw_video_paths, 1):
        proc_path = tmp_dir / f"clip_{i:02d}.mp4"
        preprocess_clip(raw_path, proc_path, clip_dur)
        processed_video_paths.append(proc_path)
        print(f"   Processed clip {i}/{n_clips}")

    # 6. Render final video
    print("\n⑥ Stitching and rendering final short video...")
    font_file = preset.get("caption_font", "CreepsterCaps.ttf")
    font_name = preset.get("caption_font_name", "Creepster")
    
    out_video = run_dir / "short.mp4"
    render_video_ltx(
        clips=processed_video_paths,
        audio_path=audio_path,
        srt_path=srt_path,
        out_video=out_video,
        total_dur=total_dur,
        tmp_dir=tmp_dir,
        font_file=font_file,
        font_name=font_name,
    )
    print(f"\n[OK] Video successfully rendered: {out_video}")

    # Clean up temp files
    shutil.rmtree(tmp_dir, ignore_errors=True)

    # 7. Upload to YouTube (optional)
    if args.upload:
        from pipeline.youtube_upload import upload_short
        yt_token_env = preset.get("yt_token_env") or "YT_REFRESH_TOKEN"
        print(f"\n⑦ YouTube: uploading ({yt_token_env})...")
        vid = upload_short(
            out_video, title, pack.get("youtube_description", ""),
            privacy_status=args.privacy,
            refresh_token_env=yt_token_env,
        )
        print(f"   Uploaded! https://www.youtube.com/shorts/{vid}")

    # 7.5 Upload to Instagram Reels (optional)
    if args.instagram:
        from pipeline.instagram_upload import publish_instagram_reel
        print("\n[Instagram] Uploading to Instagram Reels...")
        try:
            caption = pack.get("youtube_description", "")
            media_id = publish_instagram_reel(out_video, caption)
            print(f"   [Instagram] Uploaded Reel! Media ID: {media_id}")
        except Exception as e:
            print(f"   [Instagram] Upload failed: {e}")

    # 7.6 Upload to Facebook Page Reels (optional)
    if args.facebook:
        from pipeline.instagram_upload import publish_facebook_reel
        print("\n[Facebook] Uploading to Facebook Page Reels...")
        try:
            caption = pack.get("youtube_description", "")
            video_id = publish_facebook_reel(out_video, caption)
            print(f"   [Facebook] Uploaded Reel! Video ID: {video_id}")
        except Exception as e:
            print(f"   [Facebook] Upload failed: {e}")

    # Save to history
    summary = " ".join(narration.split()[:25]) + "…"
    save_title(args.channel, title, summary)

    # 8. Autoplay output video
    try:
        print(f"\nOpening final video: {out_video}")
        subprocess.Popen(["cmd", "/c", "start", "", str(out_video)])
    except Exception:
        pass

    print("\n✓ Done.")


if __name__ == "__main__":
    main()
