"""FFmpeg: images + audio + captions → vertical Short MP4 (9:16).

Effects:
  - Ken Burns: alternating zoom-in / zoom-out with directional pans
    (top-left→bottom-right, right→left, bottom-up, diagonal sweeps, etc.)
  - Cinematic crossfades between scenes (dissolve / fade / slide)
  - Bold Bebas Neue captions at the bottom third
"""
from __future__ import annotations

import random
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = REPO_ROOT / "assets" / "fonts"
DEFAULT_FONT_FILE = "BebasNeue-Regular.ttf"
DEFAULT_FONT_NAME = "Bebas Neue"

FPS = 30
FADE_DUR = 0.45          # crossfade length in seconds
ZOOM_BASE = 0.07         # base zoom amount (7%)
ZOOM_VARIANCE = 0.04     # ± variance per clip so each feels different

# Sports-appropriate transitions (no horror fadeblack)
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

# Ken Burns pan anchors: (x_expr, y_expr)
# Each tuple is (start anchor for x, start anchor for y)
# zoompan will drift from this corner toward centre
PAN_PATTERNS = [
    # zoom-in patterns — drift from corner
    ("zi", "iw/2-(iw/zoom/2)",           "ih/2-(ih/zoom/2)"),           # centre (no pan)
    ("zi", "0",                            "0"),                          # top-left anchor
    ("zi", "iw-(iw/zoom)",                "0"),                          # top-right anchor
    ("zi", "0",                            "ih-(ih/zoom)"),               # bottom-left anchor
    ("zi", "iw-(iw/zoom)",                "ih-(ih/zoom)"),               # bottom-right anchor
    # zoom-out patterns — drift toward corner
    ("zo", "iw/2-(iw/zoom/2)",           "ih/2-(ih/zoom/2)"),           # centre
    ("zo", "0",                            "ih/2-(ih/zoom/2)"),           # pan right-to-left
    ("zo", "iw-(iw/zoom)",               "ih/2-(ih/zoom/2)"),           # pan left-to-right
    ("zo", "iw/2-(iw/zoom/2)",           "0"),                          # pan down
    ("zo", "iw/2-(iw/zoom/2)",           "ih-(ih/zoom)"),               # pan up
]


def _build_zoompan(frames: int, direction: str, zoom_start: float, zoom_end: float,
                   x_expr: str, y_expr: str, width: int, height: int) -> str:
    """Build a zoompan vf string for one clip."""
    zoom_per_frame = (zoom_end - zoom_start) / max(frames - 1, 1)

    if direction == "zi":
        # zoom in: start at zoom_start, increase
        z_expr = f"min(zoom+{zoom_per_frame:.8f},{zoom_end:.6f})"
        z_init = f"if(eq(on,1),{zoom_start:.6f},zoom+{zoom_per_frame:.8f})"
        z_full = f"if(eq(on,1),{zoom_start:.6f},min(zoom+{zoom_per_frame:.8f},{zoom_end:.6f}))"
    else:
        # zoom out: start at zoom_end, decrease
        z_init = f"if(eq(on,1),{zoom_end:.6f},zoom-{zoom_per_frame:.8f})"
        z_full = f"if(eq(on,1),{zoom_end:.6f},max(zoom-{zoom_per_frame:.8f},{zoom_start:.6f}))"

    return (
        f"zoompan=z='{z_full}':"
        f"x='{x_expr}':y='{y_expr}':"
        f"d={frames}:s={width}x{height}:fps={FPS},"
        f"format=yuv420p"
    )


def render_vertical_short(
    image_paths: list[Path],
    total_duration: float,
    audio_path: Path,
    srt_path: Path,
    out_video: Path,
    *,
    width: int = 1080,
    height: int = 1920,
    font_file: str = DEFAULT_FONT_FILE,
    font_name: str = DEFAULT_FONT_NAME,
) -> None:
    if not image_paths:
        raise ValueError("No images")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found; install it (brew install ffmpeg / apt install ffmpeg)")

    out_video = Path(out_video)
    out_video.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_video.parent / "_tmp_render"
    tmp.mkdir(parents=True, exist_ok=True)

    n = len(image_paths)
    clip_dur = (total_duration + (n - 1) * FADE_DUR) / n if n > 1 else total_duration
    frames_per_clip = max(int(clip_dur * FPS), 2)

    # Pick a random transition style for this video (consistent feel across scenes)
    transition = random.choice(TRANSITIONS)

    # ── 1. Pre-scale images to 1080×1920 ────────────────────────────────────
    for i, src in enumerate(image_paths):
        dst = tmp / f"img_{i + 1:02d}.png"
        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
                "-i", str(src),
                "-vf", (
                    f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{height}"   # crop to fill — no black bars
                ),
                "-update", "1", "-frames:v", "1",
                str(dst),
            ],
            check=True,
        )

    # ── 2. Generate Ken Burns clips ──────────────────────────────────────────
    # Shuffle pan patterns so adjacent clips feel different
    patterns = random.sample(PAN_PATTERNS, min(n, len(PAN_PATTERNS)))
    if n > len(patterns):
        # If more clips than patterns, extend by repeating with shuffle
        extra = random.sample(PAN_PATTERNS, n - len(patterns))
        patterns += extra

    for i in range(n):
        src_img = tmp / f"img_{i + 1:02d}.png"
        clip = tmp / f"clip_{i + 1:02d}.mp4"

        direction, x_expr, y_expr = patterns[i]
        zoom_amount = ZOOM_BASE + random.uniform(-ZOOM_VARIANCE / 2, ZOOM_VARIANCE / 2)
        zoom_start = 1.0
        zoom_end = 1.0 + zoom_amount

        vf = _build_zoompan(
            frames_per_clip, direction, zoom_start, zoom_end,
            x_expr, y_expr, width, height,
        )

        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
                "-i", str(src_img),
                "-vf", vf,
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "15",
                str(clip),
            ],
            check=True,
        )

    # ── 3. Prepare subtitles + font ──────────────────────────────────────────
    shutil.copyfile(srt_path, tmp / "captions.srt")

    font_path = FONTS_DIR / font_file
    rendered_font_name = "Arial"
    fontsdir_arg = ""
    if font_path.is_file():
        font_dir = tmp / "_fonts"
        font_dir.mkdir(exist_ok=True)
        shutil.copyfile(font_path, font_dir / font_path.name)
        rendered_font_name = font_name
        fontsdir_arg = ":fontsdir='_fonts'"
    else:
        print(f"   [warn] Font {font_path} not found — using {rendered_font_name}")

    force_style = (
        f"FontName={rendered_font_name},"
        f"FontSize=20,"                       # slightly larger for Shorts readability
        f"PrimaryColour=&H00FFFFFF,"          # white text
        f"OutlineColour=&H00000000,"          # black outline
        f"BackColour=&HA0000000,"             # semi-transparent dark background
        f"BorderStyle=4,Outline=2,Bold=1,"
        f"Shadow=0,Alignment=2,"             # bottom center
        f"MarginV=40,MarginL=30,MarginR=30"  # breathing room from edges
    )

    # ── 4. Build xfade chain + subtitles ─────────────────────────────────────
    inputs: list[str] = []
    for i in range(n):
        inputs += ["-i", f"clip_{i + 1:02d}.mp4"]
    inputs += ["-i", str(audio_path.resolve())]

    filter_parts: list[str] = []

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
    subprocess.run(cmd, check=True, cwd=str(tmp))

    # ── cleanup ──────────────────────────────────────────────────────────────
    shutil.rmtree(tmp, ignore_errors=True)
