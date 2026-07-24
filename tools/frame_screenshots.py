from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageOps

SOURCE_DIR = Path("docs/screenshots/raw")
OUTPUT_DIR = Path("docs/screenshots")
CANVAS_SIZE = (1600, 1000)
SCREEN_BOX = (90, 120, 1510, 920)

FILES = {
    "mission-control.png": "MISSION CONTROL",
    "investigation-workspace.png": "INVESTIGATION WORKSPACE",
    "threat-intelligence.png": "THREAT INTELLIGENCE CENTER",
    "attack-surface.png": "ATTACK SURFACE INTELLIGENCE",
    "global-map.png": "GLOBAL INTELLIGENCE MAP",
    "relationship-explorer.png": "RELATIONSHIP EXPLORER",
    "ai-investigation.png": "AI INVESTIGATION",
    "reporting.png": "REPORTING & EXPORT",
}


def contain(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.convert("RGB")
    copy = image.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "#080d15")
    x = (size[0] - copy.width) // 2
    y = (size[1] - copy.height) // 2
    canvas.paste(copy, (x, y))
    return canvas


def frame_image(source: Path, destination: Path, title: str) -> None:
    canvas = Image.new("RGB", CANVAS_SIZE, "#070b12")
    draw = ImageDraw.Draw(canvas)

    # Subtle grid
    for x in range(0, CANVAS_SIZE[0], 40):
        draw.line((x, 0, x, CANVAS_SIZE[1]), fill="#0d1521", width=1)
    for y in range(0, CANVAS_SIZE[1], 40):
        draw.line((0, y, CANVAS_SIZE[0], y), fill="#0d1521", width=1)

    # Header
    draw.text((90, 52), f"BLACKTERM // {title}", fill="#f3f6fb")
    draw.text((1320, 52), "AUTHORIZED LAB", fill="#7d8ca3")

    # Glow layer
    glow = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.rounded_rectangle(SCREEN_BOX, radius=24, outline="#ff3b63", width=10)
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), glow)

    screen_w = SCREEN_BOX[2] - SCREEN_BOX[0]
    screen_h = SCREEN_BOX[3] - SCREEN_BOX[1]
    screenshot = contain(Image.open(source), (screen_w, screen_h))
    screenshot = ImageOps.expand(screenshot, border=2, fill="#35445b")

    canvas.paste(screenshot, (SCREEN_BOX[0], SCREEN_BOX[1]))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(SCREEN_BOX, radius=24, outline="#ff4d6d", width=2)

    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(destination, quality=95, optimize=True)


def main() -> None:
    missing = []
    for filename, title in FILES.items():
        source = SOURCE_DIR / filename
        if not source.exists():
            missing.append(str(source))
            continue
        frame_image(source, OUTPUT_DIR / filename, title)

    if missing:
        print("Missing source screenshots:")
        for item in missing:
            print(f"  - {item}")
        raise SystemExit(1)

    print(f"Created {len(FILES)} framed screenshots in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
