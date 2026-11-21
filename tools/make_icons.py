"""Draw the app icon (a flight-controller chip on dark) and write Android launcher PNGs into android-res/."""
import os
from PIL import Image, ImageDraw

BG = (14, 20, 27)
CHIP = (90, 163, 238)
PIN = (231, 236, 242)
DOT = (76, 195, 138)

def render(size, shape):
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shape == "square":
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.18), fill=BG)
    elif shape == "circle":
        d.ellipse([0, 0, s - 1, s - 1], fill=BG)
    else:  # full-bleed (adaptive foreground)
        d.rectangle([0, 0, s, s], fill=BG)
    k = 0.62 if shape == "bleed" else 0.9   # adaptive icons: Android masks the outer third
    c = s / 2
    half = s * 0.22 * k
    pin = max(2, int(s * 0.035 * k))
    def rect(x0, y0, x1, y1, fill):
        d.rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], fill=fill)
    for i in (-1, 0, 1):                      # pins on all four sides
        o = i * half * 0.55
        for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if sx:
                rect(c + sx * half, c + o - pin, c + sx * (half + s * 0.07 * k), c + o + pin, PIN)
            else:
                rect(c + o - pin, c + sy * half, c + o + pin, c + sy * (half + s * 0.07 * k), PIN)
    d.rounded_rectangle([c - half, c - half, c + half, c + half], radius=int(half * 0.18),
                        outline=CHIP, width=max(3, int(s * 0.03 * k)), fill=(24, 36, 50))
    r = half * 0.28
    d.ellipse([c - half * 0.55 - r * 0.0, c - half * 0.55 - r * 0.0, c - half * 0.55 + r, c - half * 0.55 + r], fill=DOT)
    return im.resize((size, size), Image.LANCZOS)

DENS = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "android-res")
for name, k in DENS.items():
    d = os.path.join(out, f"mipmap-{name}")
    os.makedirs(d, exist_ok=True)
    render(int(48 * k), "square").save(os.path.join(d, "ic_launcher.png"))
    render(int(48 * k), "circle").save(os.path.join(d, "ic_launcher_round.png"))
    render(int(108 * k), "bleed").save(os.path.join(d, "ic_launcher_foreground.png"))
render(1024, "square").save(os.path.join(out, "..", "icon-1024.png"))
print("icons written")
