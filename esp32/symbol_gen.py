from PIL import Image, ImageDraw
import numpy as np
import os

SIZE = 128
OUT_DIR = "nav_icons"

WHITE = (255, 255, 255)
GRAY = (90, 90, 90)
BG = (0, 0, 0)

os.makedirs(OUT_DIR, exist_ok=True)

# -------------------------
# RGB565
# -------------------------
def to_rgb565(img):
    arr = np.array(img.convert("RGB"), dtype=np.uint8)
    r = (arr[:, :, 0] >> 3).astype(np.uint16)
    g = (arr[:, :, 1] >> 2).astype(np.uint16)
    b = (arr[:, :, 2] >> 3).astype(np.uint16)
    return (r << 11) | (g << 5) | b

# -------------------------
# RLE ENCODER
# -------------------------
def rle_encode(pixels):
    flat = pixels.flatten()
    out = []

    last = flat[0]
    count = 1

    for p in flat[1:]:
        if p == last and count < 65535:
            count += 1
        else:
            out.append((count, int(last)))
            last = p
            count = 1

    out.append((count, int(last)))
    return out

def save_rle(path, data):
    with open(path, "wb") as f:
        for count, value in data:
            f.write(count.to_bytes(2, "little"))
            f.write(value.to_bytes(2, "little"))

# -------------------------
# ICON DRAWING
# -------------------------
def base_arrow():
    img = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)

    d.polygon([
        (58, 110),
        (70, 110),
        (70, 50),
        (85, 50),
        (64, 10),
        (45, 50),
        (58, 50),
    ], fill=WHITE)

    return img

def rotate(img, angle):
    return img.rotate(angle, resample=Image.NEAREST, expand=False)

# -------------------------
# KEEP ICONS (clean dual lane)
# -------------------------
def keep_right():
    img = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)

    # LEFT lane (gray arrow UP)
    d.polygon([
        (35, 110),
        (45, 110),
        (45, 40),
        (55, 40),
        (40, 10),
        (25, 40),
        (35, 40),
    ], fill=GRAY)

    # RIGHT lane (white arrow UP = correct path)
    d.polygon([
        (85, 110),
        (95, 110),
        (95, 40),
        (105, 40),
        (90, 10),
        (75, 40),
        (85, 40),
    ], fill=WHITE)

    return img


def keep_left():
    img = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)

    # LEFT lane (white arrow UP = correct path)
    d.polygon([
        (35, 110),
        (45, 110),
        (45, 40),
        (55, 40),
        (40, 10),
        (25, 40),
        (35, 40),
    ], fill=WHITE)

    # RIGHT lane (gray arrow UP)
    d.polygon([
        (85, 110),
        (95, 110),
        (95, 40),
        (105, 40),
        (90, 10),
        (75, 40),
        (85, 40),
    ], fill=GRAY)

    return img

# -------------------------
# ICON SET
# -------------------------
icons = {
    "up": base_arrow(),
    "slight_right": rotate(base_arrow(), -45),
    "right": rotate(base_arrow(), -90),
    "sharp_right": rotate(base_arrow(), -135),
    "slight_left": rotate(base_arrow(), 45),
    "left": rotate(base_arrow(), 90),
    "sharp_left": rotate(base_arrow(), 135),
    "keep_right": keep_right(),
    "keep_left": keep_left(),
}

# -------------------------
# BUILD RLE FILES
# -------------------------
for name, img in icons.items():
    rgb = to_rgb565(img)
    rle = rle_encode(rgb)

    save_rle(f"{OUT_DIR}/{name}.rle", rle)

    img.save(f"{OUT_DIR}/{name}.png")

    print("saved", name)