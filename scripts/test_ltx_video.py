"""
Test script: LTX-2.3 22B text-to-video via DeAPI.

Generates 3 short football video clips (~5s each) and stitches them
into a single vertical MP4 using FFmpeg — no upload to YouTube.

Output: output/ltx_test/final_test.mp4

Usage:
    python scripts/test_ltx_video.py
"""
from __future__ import annotations

import os
import random
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

DEAPI_TOKEN = os.environ.get("DEAPI_TOKEN", "").strip()
if not DEAPI_TOKEN:
    tokens_str = os.environ.get("DEAPI_TOKENS", "").strip()
    tokens = [t.strip() for t in tokens_str.split(",") if t.strip()]
    if tokens:
        DEAPI_TOKEN = tokens[0]

SUBMIT_URL  = "https://api.deapi.ai/api/v1/client/txt2video"
POLL_URL    = "https://api.deapi.ai/api/v1/client/request-status"
MODEL_SLUG  = "Ltx2_3_22B_Dist_INT8"

# 9:16 vertical — both divisible by 32, within 512-1024 limits
WIDTH   = 576
HEIGHT  = 1024
FPS     = 24
FRAMES  = 97    # ~4 seconds at 24fps

OUT_DIR = REPO_ROOT / "output" / "ltx_test"

# Football scene prompts for the test
TEST_PROMPTS = [
    (
        "A packed football stadium at night under blazing floodlights, "
        "green pitch with vivid white lines, tens of thousands of fans in national colors, "
        "massive World Cup 2026 banners, aerial drone shot slowly descending, "
        "cinematic 4K, ultra realistic, dramatic atmosphere, no text"
    ),
    (
        "A football player in a blue and white kit sprinting full speed down the right wing, "
        "motion blur on legs, packed stadium crowd roaring in background, "
        "slow motion close-up, golden hour lighting, "
        "cinematic sports photography, 4K ultra sharp, no text"
    ),
    (
        "A football player scoring a goal, arms raised in celebration, "
        "teammates rushing in to hug him, goalkeeper diving on the ground, "
        "net bulging, stadium erupting with confetti and light beams, "
        "dramatic cinematic shot, slow motion, no text"
    ),
]


def submit_video(prompt: str, client: httpx.Client) -> str:
    """Submit a txt2video job. Returns request_id."""
    headers = {
        "Authorization": f"Bearer {DEAPI_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "prompt": prompt,
        "model": MODEL_SLUG,
        "width": WIDTH,
        "height": HEIGHT,
        "fps": FPS,
        "frames": FRAMES,
        "seed": random.randint(1, 2147483647),
    }

    for attempt in range(5):
        resp = client.post(SUBMIT_URL, json=payload, headers=headers, timeout=60.0)
        if resp.status_code == 429:
            wait = 20 * (attempt + 1)
            print(f"   [429] Rate limited — waiting {wait}s...")
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            print(f"   Error response ({resp.status_code}): {resp.text}")
        resp.raise_for_status()
        break
    else:
        raise RuntimeError("429 after 5 retries")

    data = resp.json()
    request_id = data.get("data", {}).get("request_id")
    if not request_id:
        raise RuntimeError(f"No request_id in response: {data}")
    return request_id


def poll_video(request_id: str, client: httpx.Client, max_polls: int = 120) -> bytes:
    """Poll until video is ready. Returns raw video bytes."""
    headers = {
        "Authorization": f"Bearer {DEAPI_TOKEN}",
        "Accept": "application/json",
    }
    for attempt in range(1, max_polls + 1):
        time.sleep(5)
        resp = client.get(f"{POLL_URL}/{request_id}", headers=headers, timeout=30.0)
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

    raise RuntimeError(f"Timed out after {max_polls} polls")


def stitch_clips(clip_paths: list[Path], out_path: Path) -> None:
    """Concatenate clips using FFmpeg concat demuxer."""
    import shutil, subprocess

    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found")

    # Write concat list
    list_file = out_path.parent / "concat.txt"
    with open(list_file, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p.resolve()}'\n")

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    list_file.unlink(missing_ok=True)
    print(f"\n[OK] Final stitched video: {out_path}")


def main() -> None:
    if not DEAPI_TOKEN:
        print("ERROR: DEAPI_TOKEN not set in .env")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"LTX-2.3 22B Text-to-Video Test")
    print(f"Model : {MODEL_SLUG}")
    print(f"Size  : {WIDTH}x{HEIGHT} @ {FPS}fps, {FRAMES} frames (~{FRAMES/FPS:.1f}s per clip)")
    print(f"Clips : {len(TEST_PROMPTS)}")
    print(f"Output: {OUT_DIR}/final_test.mp4\n")

    clip_paths: list[Path] = []

    with httpx.Client(timeout=120.0) as client:
        for i, prompt in enumerate(TEST_PROMPTS, 1):
            print(f"[Clip {i}/{len(TEST_PROMPTS)}] Submitting...")
            print(f"   Prompt: {prompt[:80]}...")

            request_id = submit_video(prompt, client)
            print(f"   Job ID: {request_id}")

            video_bytes = poll_video(request_id, client)

            clip_path = OUT_DIR / f"clip_{i:02d}.mp4"
            clip_path.write_bytes(video_bytes)
            print(f"   Saved: {clip_path} ({len(video_bytes)//1024}KB)")
            clip_paths.append(clip_path)

            if i < len(TEST_PROMPTS):
                print("   Cooldown 10s before next clip...")
                time.sleep(10)

    # Stitch all clips together
    final = OUT_DIR / "final_test.mp4"
    stitch_clips(clip_paths, final)

    # Open in default player
    import subprocess
    try:
        subprocess.Popen(["cmd", "/c", "start", "", str(final)])
    except Exception:
        pass

    print(f"\nDone! Open: {final}")


if __name__ == "__main__":
    main()
