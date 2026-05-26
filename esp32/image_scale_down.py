from PIL import Image
import os

# --------------------
# CONFIG
# --------------------
INPUT_FOLDER = "images"
OUTPUT_FOLDER = "images_resized"

DISPLAY_W = 320
DISPLAY_H = 480

SUPPORTED = (".png", ".jpg", ".jpeg")

# --------------------
# SETUP OUTPUT DIR
# --------------------
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --------------------
# PROCESS FILES
# --------------------
for filename in os.listdir(INPUT_FOLDER):
    if not filename.lower().endswith(SUPPORTED):
        continue

    input_path = os.path.join(INPUT_FOLDER, filename)
    output_path = os.path.join(OUTPUT_FOLDER, filename)

    try:
        img = Image.open(input_path)

        # Keep aspect ratio, fit into screen
        img.thumbnail((DISPLAY_W, DISPLAY_H))

        # Create black background (optional but stable for TFTs)
        canvas = Image.new("RGB", (DISPLAY_W, DISPLAY_H), (0, 0, 0))

        # Center image
        x = (DISPLAY_W - img.width) // 2
        y = (DISPLAY_H - img.height) // 2
        canvas.paste(img, (x, y))

        # Save optimized
        if filename.lower().endswith(".png"):
            canvas.save(output_path, optimize=True)
        else:
            canvas.save(output_path, quality=85, optimize=True)

        print(f"OK: {filename}")

    except Exception as e:
        print(f"FAIL: {filename} -> {e}")