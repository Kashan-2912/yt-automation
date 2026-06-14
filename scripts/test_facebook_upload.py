"""Test script: Upload an existing MP4 to Facebook Page Reels via Meta Graph API.

Usage:
    python scripts/test_facebook_upload.py --video path/to/video.mp4 --caption "My awesome reel! #Shorts"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from pipeline.instagram_upload import publish_facebook_reel


def find_latest_rendered_video() -> Path | None:
    """Find the most recently rendered short.mp4 in output/runs."""
    runs_dir = REPO_ROOT / "output" / "runs"
    if not runs_dir.is_dir():
        return None
    
    candidates = list(runs_dir.glob("**/short.mp4"))
    if not candidates:
        return None
        
    # Sort by modification time descending
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def main() -> None:
    ap = argparse.ArgumentParser(description="Upload a video to Facebook Page Reels.")
    ap.add_argument("--video", default="", help="Path to the MP4 file to upload. If empty, uses latest rendered short.")
    ap.add_argument("--caption", default="Test Facebook Page Reels upload! #FIFA2026 #WorldCup #Reels", help="Reel caption.")
    args = ap.parse_args()

    video_path_str = args.video.strip()
    if video_path_str:
        video_path = Path(video_path_str)
    else:
        print("Searching for latest rendered video in output/runs...")
        video_path = find_latest_rendered_video()
        if not video_path:
            print("ERROR: No video path provided, and no rendered short.mp4 found in output/runs.")
            sys.exit(1)

    if not video_path.is_file():
        print(f"ERROR: Video file not found: {video_path}")
        sys.exit(1)

    print(f"Target Video : {video_path}")
    print(f"Caption      : {args.caption}\n")

    try:
        video_id = publish_facebook_reel(video_path, args.caption)
        print(f"\n[OK] Video successfully uploaded to Facebook! Video ID: {video_id}")
    except Exception as e:
        print(f"\n[ERROR] Facebook upload failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
