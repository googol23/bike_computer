
import framebuf

ARROW_SIZE = 128
ARROW_COUNT = 8

SIGN_TO_FILE = {
    0: "up",
    1: "slight_right",
    2: "right",
    3: "sharp_right",
    -1: "slight_left",
    -2: "left",
    -3: "sharp_left",
    7: "keep_right",
    -7: "keep_left",
}

class ArrowSprites:
    def __init__(self, display, sign, w=128, h=128):
        path = f"nav_icons/{SIGN_TO_FILE[sign]}.rle"
        print(path)
        self.display = display
        self.w = w
        self.h = h

        with open(path, "rb") as f:
            self.data = f.read()

        self.pixels = bytearray(w * h * 2)

        self._decode()

    def _decode(self):
        i = 0
        j = 0

        while i < len(self.data):
            count = int.from_bytes(self.data[i:i+2], "little")
            value = int.from_bytes(self.data[i+2:i+4], "little")
            i += 4

            for _ in range(count):
                self.pixels[j] = value & 0xFF
                self.pixels[j+1] = value >> 8
                j += 2

    def blit(self, x, y):
        w = self.w

        for row in range(self.h):
            src = row * w * 2
            dst = ((y + row) * self.display.w + x) * 2

            self.display.buffer[dst:dst + w * 2] = \
                self.pixels[src:src + w * 2]

        self.display._mark_dirty(x, y, self.w, self.h)