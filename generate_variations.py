"""
generate_variations.py — Create ffmpeg audio variations of training videos.

For each input video, produces 2 variations:
  - _firm: slightly faster tempo, louder (simulates firm/urgent tone)
  - _gentle: slightly slower tempo, softer (simulates gentle/patient tone)
"""

import os
import subprocess
import sys
from pathlib import Path

VIDEOS_DIR = Path("videos")
VARIATIONS = [
    ("_firm",   ["-filter:a", "atempo=1.15,volume=1.4"]),
    ("_gentle", ["-filter:a", "atempo=0.88,volume=0.75"]),
]


def make_variation(src: Path, suffix: str, audio_filters: list[str]) -> Path:
    out = VIDEOS_DIR / f"{src.stem}{suffix}{src.suffix}"
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        *audio_filters,
        "-c:v", "copy",
        str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def main():
    sources = sorted(
        p for p in VIDEOS_DIR.iterdir()
        if p.suffix.upper() in {".MP4", ".MOV", ".M4V"}
        and not any(p.stem.endswith(s) for s, _ in VARIATIONS)
    )

    print(f"Generating variations for {len(sources)} source videos...\n")
    generated = []
    for src in sources:
        for suffix, filters in VARIATIONS:
            out = make_variation(src, suffix, filters)
            print(f"  {src.name} → {out.name}")
            generated.append(out)

    print(f"\nDone. {len(generated)} variation files created.")
    return generated


if __name__ == "__main__":
    main()
