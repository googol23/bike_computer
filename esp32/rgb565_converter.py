from PIL import Image
import numpy as np
import os

INPUT_DIR = "images"
OUTPUT_DIR = "rgb565"

WIDTH = 320
HEIGHT = 480

os.makedirs(OUTPUT_DIR, exist_ok=True)

def convert_image(path, out_path):
    img = Image.open(path).convert("RGB")
    img = img.resize((WIDTH, HEIGHT))

    pixels = np.array(img)

    with open(out_path, "wb") as f:
        for y in range(HEIGHT):
            for x in range(WIDTH):
                r, g, b = pixels[y][x]
                rgb565 = ((b & 0xF8) << 8) | ((g & 0xFC) << 3) | (r >> 3)
                f.write(int(rgb565).to_bytes(2, "little"))

    print(f"Converted: {path} -> {out_path}")

def main():
    for file in os.listdir(INPUT_DIR):
        if not file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
            continue

        input_path = os.path.join(INPUT_DIR, file)
        name = os.path.splitext(file)[0]
        output_path = os.path.join(OUTPUT_DIR, name + ".rgb565")

        try:
            convert_image(input_path, output_path)
        except Exception as e:
            print(f"Failed: {file} -> {e}")

if __name__ == "__main__":
    main()