"""
generate_dog_states.py — Generate animated GIF clips for each dog emotional state.

Uses Imagen 4 to generate golden retriever images per state,
then animates them with PIL into looping GIFs.

Run once: python generate_dog_states.py
Outputs: dog_states/happy.gif, confused.gif, confident.gif, alert.gif
"""

from dotenv import load_dotenv
load_dotenv()

import io
import math
import os
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

STATES_DIR = Path("dog_states")
STATES_DIR.mkdir(exist_ok=True)

MODEL   = "imagen-4.0-fast-generate-001"
SIZE    = 300  # final GIF size

PROMPTS = {
    "happy": (
        "A cute golden retriever puppy bouncing with joy, mouth open in a big happy smile, "
        "tail wagging, paws in the air, cartoon illustration style, clean white background, "
        "vibrant colors, no text, no humans"
    ),
    "confused": (
        "A golden retriever dog with head tilted far to one side looking very puzzled and "
        "confused, one ear flopped, big question-mark eyes, cartoon illustration style, "
        "clean white background, vibrant colors, no text, no humans"
    ),
    "confident": (
        "A golden retriever dog sitting tall and proud, chest puffed out, chin up, "
        "looking calm and self-assured, cartoon illustration style, clean white background, "
        "vibrant colors, no text, no humans"
    ),
    "alert": (
        "A golden retriever dog with both ears fully perked up, eyes wide open and "
        "intensely focused, body leaning forward on high alert, cartoon illustration style, "
        "clean white background, vibrant colors, no text, no humans"
    ),
}


def generate_image(prompt: str) -> Image.Image:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_images(
        model=MODEL,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="1:1",
        ),
    )
    raw = response.generated_images[0].image.image_bytes
    img = Image.open(io.BytesIO(raw)).convert("RGBA")
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def _to_rgb(img: Image.Image) -> Image.Image:
    bg = Image.new("RGB", img.size, (255, 255, 255))
    if img.mode == "RGBA":
        bg.paste(img, mask=img.split()[3])
    else:
        bg.paste(img)
    return bg


def _save(frames: list, path: Path, duration: int) -> None:
    rgb = [_to_rgb(f) for f in frames]
    rgb[0].save(
        path,
        save_all=True,
        append_images=rgb[1:],
        loop=0,
        duration=duration,
        optimize=True,
    )
    print(f"  saved {path}  ({len(frames)} frames)")


def animate_happy(src: Image.Image) -> None:
    """Bounce up and down."""
    pad, n = 24, 16
    frames = []
    for i in range(n):
        t      = i / n
        offset = int(pad * abs(math.sin(t * math.pi * 2)))
        canvas = Image.new("RGBA", (SIZE, SIZE + pad), (255, 255, 255, 0))
        canvas.paste(src, (0, pad - offset), src)
        frames.append(canvas.crop((0, 0, SIZE, SIZE)))
    _save(frames, STATES_DIR / "happy.gif", duration=50)


def animate_confused(src: Image.Image) -> None:
    """Rock side to side."""
    n = 20
    frames = []
    for i in range(n):
        t     = i / n
        angle = 12 * math.sin(t * math.pi * 2)
        frames.append(src.rotate(angle, resample=Image.BICUBIC, expand=False))
    _save(frames, STATES_DIR / "confused.gif", duration=65)


def animate_confident(src: Image.Image) -> None:
    """Slow proud pulse."""
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


def animate_alert(src: Image.Image) -> None:
    """Sharp pop then attentive hold."""
    frames = []
    for i in range(6):          # pop-in
        t     = i / 5
        scale = 0.88 + 0.18 * t
        ns    = (int(SIZE * scale), int(SIZE * scale))
        rs    = src.resize(ns, Image.LANCZOS)
        canvas = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
        x = (SIZE - ns[0]) // 2
        y = (SIZE - ns[1]) // 2
        canvas.paste(rs, (x, y), rs)
        frames.append(canvas)
    for i in range(16):         # attentive pulse
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


ANIMATORS = {
    "happy":     animate_happy,
    "confused":  animate_confused,
    "confident": animate_confident,
    "alert":     animate_alert,
}

if __name__ == "__main__":
    for state, prompt in PROMPTS.items():
        print(f"\n[{state}] Generating image with Imagen 4...")
        img = generate_image(prompt)
        img.save(STATES_DIR / f"{state}_base.png")   # keep base for inspection
        print(f"[{state}] Animating...")
        ANIMATORS[state](img)
    print("\nDone — dog_states/ ready.")
