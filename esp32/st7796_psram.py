"""Fast ST7796 RGB565 framebuffer driver for MicroPython / ESP32-S3.

Designed for a 320x480 ST7796 panel connected over SPI and an ESP32-S3
with PSRAM (for example N16R8).  The public drawing API is compatible with
this project's HUD/widgets: clear, fill_rect, pixel, line, circle,
triangle_*, text, blit, flush and flush_full.
"""

import math
import time
import framebuf
from machine import Pin, SPI, PWM

import config
import arial16
import arial24
import arial30


# ST7796 commands
_SWRESET = 0x01
_SLPOUT = 0x11
_NORON = 0x13
_INVOFF = 0x20
_INVON = 0x21
_DISPON = 0x29
_CASET = 0x2A
_RASET = 0x2B
_RAMWR = 0x2C
_MADCTL = 0x36
_COLMOD = 0x3A

_FONT_MAP = {
    16: arial16,
    24: arial24,
    30: arial30,
}

try:
    _isqrt = math.isqrt
except AttributeError:
    def _isqrt(value):
        return int(value ** 0.5)


class ST7796DisplayPSRAM:
    """Full-framebuffer ST7796 driver optimized for ESP32-S3 + PSRAM.

    Performance characteristics:
    - 320x480 RGB565 framebuffer: 307,200 bytes.
    - Full-screen flush is one SPI.write() call with no copied slices.
    - Partial-width dirty rectangles use zero-copy memoryview row views.
    - Drawing primitives operate in framebuf, not over SPI.

    At 40 MHz, the wire-time lower bound for a full frame is about 61.4 ms,
    or 16.3 FPS. Real throughput depends on the MicroPython build, PSRAM,
    wiring and panel. 10 FPS requires a measured full flush below 100 ms.
    """

    def __init__(
        self,
        width:int,
        height:int,
        spi:SPI,
        pin_cs=config.DISPLAY_PIN_CS,
        pin_rst=config.DISPLAY_PIN_RST,
        pin_dc=config.DISPLAY_PIN_DC,
        pin_led=config.DISPLAY_PIN_LED,
        rotation=0,
        invert=False,
        bgr=True,
        x_offset=0,
        y_offset=0,
        glyph_cache_size=48,
    ):
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive")

        self.w = int(width)
        self.h = int(height)
        self.width = self.w
        self.height = self.h
        
        self.spi = spi
        self.x_offset = int(x_offset)
        self.y_offset = int(y_offset)
        self._glyph_cache_size = max(0, int(glyph_cache_size))
        self._glyph_cache = {}

        # On PSRAM-enabled ESP32-S3 MicroPython builds, a large bytearray is
        # normally allocated from the heap backed by external RAM.
        self.buffer = bytearray(self.w * self.h * 2)
        self._buffer_view = memoryview(self.buffer)
        self.fb = framebuf.FrameBuffer(
            self.buffer, self.w, self.h, framebuf.RGB565
        )

        # Reused command/data buffers: no allocation in set_window().
        self._one = bytearray(1)
        self._window = bytearray(4)

        self.cs = Pin(pin_cs, Pin.OUT, value=1)
        self.dc = Pin(pin_dc, Pin.OUT, value=1)
        self.rst = Pin(pin_rst, Pin.OUT, value=1)

        self.led = PWM(Pin(pin_led), freq=1000)
        self.set_backlight(100)

        self._dirty = False
        self._dx0 = self.w
        self._dy0 = self.h
        self._dx1 = -1
        self._dy1 = -1

        self._rotation = rotation
        self._bgr = bool(bgr)
        self._invert = bool(invert)
        self._init_display()

    def _prepare_spi(self):
        self.spi.init(
            baudrate=config.DISPLAY_BAUDRATE,
            polarity=0,
            phase=0,
        )

    # ------------------------------------------------------------------
    # Hardware and controller setup
    # ------------------------------------------------------------------
    def set_backlight(self, level):
        level = max(0, min(100, int(level)))
        if hasattr(self.led, "duty_u16"):
            self.led.duty_u16((level * 65535) // 100)
        else:
            self.led.duty((level * 1023) // 100)

    def _write_cmd(self, command, data=None):
        self._one[0] = command
        self.cs(0)
        self.dc(0)
        self.spi.write(self._one)
        if data is not None:
            self.dc(1)
            self.spi.write(data)
        self.cs(1)

    # Compatibility with the older class.
    def _cmd(self, command):
        self._write_cmd(command)

    def _data(self, data):
        if isinstance(data, int):
            self._one[0] = data
            data = self._one
        self.cs(0)
        self.dc(1)
        self.spi.write(data)
        self.cs(1)

    def _reset(self):
        self.rst(1)
        time.sleep_ms(20)
        self.rst(0)
        time.sleep_ms(20)
        self.rst(1)
        time.sleep_ms(120)

    def _madctl(self):
        # MX=0x40, MY=0x80, MV=0x20, BGR=0x08
        rotation = self._rotation % 360
        values = {
            0: 0x40,
            90: 0x20,
            180: 0x80,
            270: 0xE0,
        }
        if rotation not in values:
            raise ValueError("rotation must be 0, 90, 180 or 270")
        return values[rotation] | (0x08 if self._bgr else 0)

    def _init_display(self):
        self._reset()

        self._cmd(0x01)  # SW reset
        time.sleep_ms(150)

        self._cmd(0x11)  # Sleep out
        time.sleep_ms(150)

        self._cmd(0x3A)  # Pixel format
        self._data(0x55)  # RGB565

        self._cmd(0x36)  # MADCTL
        self._data(0x48)


        self._cmd(0x29)  # Display on
        time.sleep_ms(50)

    # ------------------------------------------------------------------
    # Dirty rectangle handling
    # ------------------------------------------------------------------
    def _mark_dirty(self, x, y, w, h):
        if w <= 0 or h <= 0:
            return

        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(self.w - 1, int(x) + int(w) - 1)
        y1 = min(self.h - 1, int(y) + int(h) - 1)
        if x0 > x1 or y0 > y1:
            return

        if not self._dirty:
            self._dx0, self._dy0 = x0, y0
            self._dx1, self._dy1 = x1, y1
            self._dirty = True
            return

        if x0 < self._dx0:
            self._dx0 = x0
        if y0 < self._dy0:
            self._dy0 = y0
        if x1 > self._dx1:
            self._dx1 = x1
        if y1 > self._dy1:
            self._dy1 = y1

    def mark_full_dirty(self):
        self._dirty = True
        self._dx0 = 0
        self._dy0 = 0
        self._dx1 = self.w - 1
        self._dy1 = self.h - 1

    def _clear_dirty(self):
        self._dirty = False
        self._dx0 = self.w
        self._dy0 = self.h
        self._dx1 = -1
        self._dy1 = -1

    # ------------------------------------------------------------------
    # LCD transfer
    # ------------------------------------------------------------------
    def set_window(self, x0, y0, x1, y1):
        x0 += self.x_offset
        x1 += self.x_offset
        y0 += self.y_offset
        y1 += self.y_offset

        b = self._window
        b[0] = (x0 >> 8) & 0xFF
        b[1] = x0 & 0xFF
        b[2] = (x1 >> 8) & 0xFF
        b[3] = x1 & 0xFF
        self._write_cmd(_CASET, b)

        b[0] = (y0 >> 8) & 0xFF
        b[1] = y0 & 0xFF
        b[2] = (y1 >> 8) & 0xFF
        b[3] = y1 & 0xFF
        self._write_cmd(_RASET, b)
        self._write_cmd(_RAMWR)

    def flush(self):
        """Flush the accumulated dirty bounding rectangle.

        Returns elapsed milliseconds, or 0 when nothing was dirty.
        """
        if not self._dirty:
            return 0

        self._prepare_spi()

        x0, y0 = self._dx0, self._dy0
        x1, y1 = self._dx1, self._dy1
        t0 = time.ticks_ms()
        self.set_window(x0, y0, x1, y1)

        self.cs(0)
        self.dc(1)

        if x0 == 0 and x1 == self.w - 1:
            # Rows are contiguous, so this is one zero-copy SPI transaction.
            start = y0 * self.w * 2
            end = (y1 + 1) * self.w * 2
            self.spi.write(self._buffer_view[start:end])
        else:
            # A rectangular subsection is not contiguous in a row-major
            # framebuffer. memoryview slices avoid allocating row copies.
            row_bytes = (x1 - x0 + 1) * 2
            stride = self.w * 2
            offset = y0 * stride + x0 * 2
            for _ in range(y0, y1 + 1):
                self.spi.write(self._buffer_view[offset:offset + row_bytes])
                offset += stride

        self.cs(1)
        self._clear_dirty()
        return time.ticks_diff(time.ticks_ms(), t0)

    def flush_full(self):
        """Force one zero-copy full-screen transfer and return elapsed ms."""
        t0 = time.ticks_ms()
        self._prepare_spi()
        self.set_window(0, 0, self.w - 1, self.h - 1)
        self.cs(0)
        self.dc(1)
        self.spi.write(self._buffer_view)
        self.cs(1)
        self._clear_dirty()
        return time.ticks_diff(time.ticks_ms(), t0)

    def benchmark(self, frames=20):
        """Measure full-screen transfer rate. Returns (average_ms, fps)."""
        frames = max(1, int(frames))
        start = time.ticks_ms()
        for _ in range(frames):
            self.flush_full()
        elapsed = time.ticks_diff(time.ticks_ms(), start)
        average_ms = elapsed / frames
        fps = 1000.0 / average_ms if average_ms else 0.0
        return average_ms, fps

    # ------------------------------------------------------------------
    # Framebuffer drawing API
    # ------------------------------------------------------------------
    def clear(self, color=0x0000):
        self.fb.fill(color & 0xFFFF)
        self.mark_full_dirty()

    def pixel(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.fb.pixel(x, y, color & 0xFFFF)
            self._mark_dirty(x, y, 1, 1)

    def fill_rect(self, x, y, w, h, color):
        if w <= 0 or h <= 0:
            return
        self.fb.fill_rect(x, y, w, h, color & 0xFFFF)
        self._mark_dirty(x, y, w, h)

    def line(self, x0, y0, x1, y1, color):
        self.fb.line(x0, y0, x1, y1, color & 0xFFFF)
        self._mark_dirty(
            min(x0, x1), min(y0, y1),
            abs(x1 - x0) + 1, abs(y1 - y0) + 1,
        )

    def circle(self, cx, cy, radius, color):
        """Draw a filled circle."""
        radius = int(radius)
        if radius < 0:
            return
        if radius == 0:
            self.pixel(cx, cy, color)
            return

        rr = radius * radius
        for dy in range(-radius, radius + 1):
            py = cy + dy
            if py < 0 or py >= self.h:
                continue
            dx = _isqrt(rr - dy * dy)
            left = max(0, cx - dx)
            right = min(self.w - 1, cx + dx)
            if left <= right:
                self.fb.fill_rect(left, py, right - left + 1, 1, color & 0xFFFF)
        self._mark_dirty(cx - radius, cy - radius, radius * 2 + 1, radius * 2 + 1)

    def _triangle(self, x1, y1, x2, y2, x3, y3, color):
        self.fb.line(x1, y1, x2, y2, color & 0xFFFF)
        self.fb.line(x2, y2, x3, y3, color & 0xFFFF)
        self.fb.line(x3, y3, x1, y1, color & 0xFFFF)
        x0 = min(x1, x2, x3)
        y0 = min(y1, y2, y3)
        self._mark_dirty(x0, y0, max(x1, x2, x3) - x0 + 1,
                         max(y1, y2, y3) - y0 + 1)

    def triangle_up(self, cx, cy, size, color):
        half_width = int(size * 0.8660254)
        self._triangle(cx, cy - size,
                       cx - half_width, cy + size // 2,
                       cx + half_width, cy + size // 2, color)

    def triangle_down(self, cx, cy, size, color):
        half_width = int(size * 0.8660254)
        self._triangle(cx, cy + size,
                       cx - half_width, cy - size // 2,
                       cx + half_width, cy - size // 2, color)

    def triangle_left(self, cx, cy, size, color):
        half_height = int(size * 0.8660254)
        self._triangle(cx - size, cy,
                       cx + size // 2, cy - half_height,
                       cx + size // 2, cy + half_height, color)

    def triangle_right(self, cx, cy, size, color):
        half_height = int(size * 0.8660254)
        self._triangle(cx + size, cy,
                       cx - size // 2, cy - half_height,
                       cx - size // 2, cy + half_height, color)

    # ------------------------------------------------------------------
    # Text
    # ------------------------------------------------------------------
    def _get_glyph(self, char, font_size):
        key = (font_size, char)
        cached = self._glyph_cache.get(key)
        if cached is not None:
            return cached

        font = _FONT_MAP.get(font_size)
        if font is None:
            raise ValueError("font_size must be 8, 16, 24 or 30")

        glyph, glyph_h, glyph_w = font.get_ch(char)
        glyph_buffer = bytearray(glyph)
        glyph_fb = framebuf.FrameBuffer(
            glyph_buffer, glyph_w, glyph_h, framebuf.MONO_HLSB
        )
        result = (glyph_fb, glyph_w, glyph_h, glyph_buffer)

        if self._glyph_cache_size:
            if len(self._glyph_cache) >= self._glyph_cache_size:
                self._glyph_cache.pop(next(iter(self._glyph_cache)))
            self._glyph_cache[key] = result
        return result

    @staticmethod
    def _rgb565_palette(foreground, background):
        # framebuf RGB565 uses native two-byte storage. Constructing this via
        # FrameBuffer.pixel() avoids hard-coding byte order.
        palette_buffer = bytearray(4)
        palette = framebuf.FrameBuffer(palette_buffer, 2, 1, framebuf.RGB565)
        palette.pixel(0, 0, background & 0xFFFF)
        palette.pixel(1, 0, foreground & 0xFFFF)
        return palette, palette_buffer

    def text(self, x, y, w, h, string, color, bg=0x0000, font_size=30):
        """Draw clipped text into the framebuffer.

        The supplied rectangle is cleared to bg first, matching TextWidget's
        expected behavior and preventing remnants of a previous longer value.
        """
        if w <= 0 or h <= 0:
            return

        self.fb.fill_rect(x, y, w, h, bg & 0xFFFF)
        string = str(string)

        if font_size == 8:
            # Built-in framebuf font is 8x8.
            max_chars = max(0, w // 8)
            max_lines = max(1, h // 8)
            cy = y
            line_count = 0
            for source_line in string.split("\n"):
                start = 0
                while start < len(source_line) or (not source_line and start == 0):
                    if line_count >= max_lines:
                        break
                    part = source_line[start:start + max_chars] if max_chars else ""
                    self.fb.text(part, x, cy, color & 0xFFFF)
                    cy += 8
                    line_count += 1
                    if not source_line or max_chars == 0:
                        break
                    start += max_chars
                if line_count >= max_lines:
                    break
            self._mark_dirty(x, y, w, h)
            return

        palette, palette_buffer = self._rgb565_palette(color, bg)
        # Keep palette_buffer alive for the duration of all blits.
        _ = palette_buffer
        cx = x
        cy = y
        line_height = font_size
        right = x + w
        bottom = y + h
        spacing = 2

        for char in string:
            if char == "\n":
                cx = x
                cy += line_height
                if cy >= bottom:
                    break
                continue

            glyph_fb, glyph_w, glyph_h, glyph_buffer = self._get_glyph(char, font_size)
            _ = glyph_buffer
            if cx + glyph_w > right:
                cx = x
                cy += line_height
            if cy + glyph_h > bottom:
                break

            # Native C framebuf blit with a two-entry RGB565 palette; avoids
            # Python pixel-by-pixel glyph loops.
            self.fb.blit(glyph_fb, cx, cy, -1, palette)
            cx += glyph_w + spacing

        self._mark_dirty(x, y, w, h)

    # ------------------------------------------------------------------
    # Bitmap/sprite support
    # ------------------------------------------------------------------
    def blit(self, source, x, y, w=None, h=None, key=-1, palette=None):
        """Blit a FrameBuffer, or an RGB565 bytes-like object, into this buffer.

        FrameBuffer form:
            display.blit(sprite_fb, x, y)

        Raw RGB565 form:
            display.blit(raw_buffer, x, y, width, height)
        """
        if hasattr(source, "pixel"):
            self.fb.blit(source, x, y, key, palette)
            # framebuf does not expose dimensions. Callers should provide w/h
            # for precise dirty tracking; otherwise conservatively mark all.
            if w is None or h is None:
                self.mark_full_dirty()
            else:
                self._mark_dirty(x, y, w, h)
            return

        if w is None or h is None:
            raise ValueError("raw blit requires width and height")
        source_fb = framebuf.FrameBuffer(source, w, h, framebuf.RGB565)
        self.fb.blit(source_fb, x, y, key, palette)
        self._mark_dirty(x, y, w, h)

    def show_logo(self, filename):
        """Load a raw RGB565 full-screen image into the framebuffer."""
        expected = len(self.buffer)
        with open(filename, "rb") as source:
            read = source.readinto(self.buffer)
        if read != expected:
            raise ValueError("logo must contain exactly %d RGB565 bytes" % expected)
        self.mark_full_dirty()
        return self.flush_full()