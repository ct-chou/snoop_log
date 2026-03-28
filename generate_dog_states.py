"""
generate_dog_states.py — Generate animated GIF clips for each dog emotional state.

Run once: python generate_dog_states.py
Outputs: dog_states/happy.gif, confused.gif, confident.gif, alert.gif
"""

import math
from pathlib import Path
from PIL import Image

STATES_DIR = Path("dog_states")
STATES_DIR.mkdir(exist_ok=True)
SRC_PATH   = Path("images/snooplogclean.PNG")
SIZE       = 280  # render size — smaller = smaller GIF, better palette


def _open() -> Image.Image:
    return Image.open(SRC_PATH).convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)


def _to_rgb(img: Image.Image) -> Image.Image:
    bg = Image.new("RGB", img.size, (255, 255, 255))
    bg.paste(img, mask=img.split()[3])
    return bg


def _save(frames_rgba: list, path: Path, duration: int = 55) -> None:
    rgb = [_to_rgb(f) for f in frames_rgba]
    rgb[0].save(
        path,
        save_all=True,
        append_images=rgb[1:],
        loop=0,
        duration=duration,
        optimize=True,
    )
    print(f"  saved {path}  ({len(frames_rgba)} frames, {duration}ms/frame)")


def make_happy() -> None:
    """Bounce up and down — reward received!"""
    src = _open()
    n, pad = 16, 22
    frames = []
    for i in range(n):
        t      = i / n
        offset = int(pad * abs(math.sin(t * math.pi * 2)))
        canvas = Image.new("RGBA", (SIZE, SIZE + pad), (255, 255, 255, 0))
        canvas.paste(src, (0, pad - offset), src)
        frames.append(canvas.crop((0, 0, SIZE, SIZE)))
    _save(frames, STATES_DIR / "happy.gif", duration=50)


def make_confused() -> None:
    """Rock left and right — contradictory signal!"""
    src = _open()
    n = 20
    frames = []
    for i in range(n):
        t      = i / n
        angle  = 11 * math.sin(t * math.pi * 2)
        rotated = src.rotate(angle, resample=Image.BICUBIC, expand=False)
        frames.append(rotated)
    _save(frames, STATES_DIR / "confused.gif", duration=65)


def make_confident() -> None:
    """Steady proud pulse — I know this one."""
    src = _open()
    n = 22
    frames = []
    for i in range(n):
        t     = i / n
        scale = 1.0 + 0.065 * math.sin(t * math.pi * 2)
        ns    = (int(SIZE * scale), int(SIZE * scale))
        rs    = src.resize(ns, Image.LANCZOS)
        canvas = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
        x = (SIZE - ns[0]) // 2
        y = (SIZE - ns[1]) // 2
        canvas.paste(rs, (x, y), rs)
        frames.append(canvas)
    _save(frames, STATES_DIR / "confident.gif", duration=70)


def make_alert() -> None:
    """Sharp pop then attentive hold — something caught my attention!"""
    src = _open()
    frames = []

    # Quick pop-in (6 frames)
    for i in range(6):
        t     = i / 5
        scale = 0.88 + 0.18 * t          # 0.88 → 1.04
        ns    = (int(SIZE * scale), int(SIZE * scale))
        rs    = src.resize(ns, Image.LANCZOS)
        canvas = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
        x = (SIZE - ns[0]) // 2
        y = (SIZE - ns[1]) // 2
        canvas.paste(rs, (x, y), rs)
        frames.append(canvas)

    # Slow attentive pulse (16 frames)
    for i in range(16):
        t     = i / 15
        scale = 1.0 + 0.04 * math.sin(t * math.pi * 2)
        ns    = (int(SIZE * scale), int(SIZE * scale))
        rs    = src.resize(ns, Image.LANCZOS)
        canvas = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
        x = (SIZE - ns[0]) // 2
        y = (SIZE - ns[1]) // 2
        canvas.paste(rs, (x, y), rs)
        frames.append(canvas)

    _save(frames, STATES_DIR / "alert.gif", duration=52)


if __name__ == "__main__":
    print("Generating dog state GIFs from", SRC_PATH)
    make_happy()
    make_confused()
    make_confident()
    make_alert()
    print("Done — dog_states/ ready.")
