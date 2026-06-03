import re
import config
from machine import Pin, SPI, PWM
import time

import framebuf

import arial16
import arial24
import arial30


MAX_CACHE = 16
# -------------------------
# DISPLAY DRIVER (FAST CORE)
# -------------------------
class ST7796Display:
    def __init__(
        self,
        width,
        height,
        pin_cs=config.DISPLAY_PIN_CS,
        pin_rst=config.DISPLAY_PIN_RST,
        pin_dc=config.DISPLAY_PIN_DC,
        pin_mosi=config.DISPLAY_PIN_MOSI,
        pin_sck=config.DISPLAY_PIN_SCK,
        pin_miso=config.DISPLAY_PIN_MISO,
        pin_led=config.DISPLAY_PIN_LED,
        spi_id=2,
        baudrate=40_000_000,
    ):
        self.glyph_cache = {}        
        self.buf = bytearray(4096)

        self.w = width
        self.h = height

        self.cs = Pin(pin_cs, Pin.OUT, value=1)
        self.dc = Pin(pin_dc, Pin.OUT, value=1)
        self.rst = Pin(pin_rst, Pin.OUT, value=1)

        self.led = PWM(Pin(pin_led), freq=1000)
        self.led.duty(1023)  # full brightness (ESP32: 0–1023)

        self.spi = SPI(
            spi_id,
            baudrate=baudrate,
            polarity=0,
            phase=0,
            sck=Pin(pin_sck),
            mosi=Pin(pin_mosi),
            miso=Pin(pin_miso),
        )

        self._init_display()

    def set_backlight(self, level):
        """
        level: 0–100 (% brightness)
        """
        level = max(0, min(100, level))
        duty = int((level / 100) * 1023)
        self.led.duty(duty)
        
    def _get_glyph(self, ch):
        if ch in self.glyph_cache:
            return self.glyph_cache[ch]
    
        glyph, gh, gw = arial30.get_ch(ch)
    
        fb = framebuf.FrameBuffer(
            bytearray(glyph),
            gw,
            gh,
            framebuf.MONO_HLSB
        )
    
        self.glyph_cache[ch] = (fb, gw, gh)
    
        if len(self.glyph_cache) > MAX_CACHE:
            self.glyph_cache.pop(next(iter(self.glyph_cache)))
    
        return fb, gw, gh
        
    # -------------------------
    # LOW LEVEL
    # -------------------------
    def _cmd(self, c):
        self.cs.value(0)
        self.dc.value(0)
        self.spi.write(bytearray([c]))
        self.cs.value(1)

    def _data(self, d):
        self.cs.value(0)
        self.dc.value(1)
        self.spi.write(d if isinstance(d, (bytes, bytearray))
                       else bytearray([d]))
        self.cs.value(1)

    def _start(self):
        self.cs.value(0)
        self.dc.value(1)

    def _end(self):
        self.cs.value(1)

    # -------------------------
    # INIT
    # -------------------------
    def _reset(self):
        self.rst.value(1)
        time.sleep_ms(50)
        self.rst.value(0)
        time.sleep_ms(100)
        self.rst.value(1)
        time.sleep_ms(150)

    def _init_display(self):
        print("Display init started")
        self._reset()

        self._cmd(0x01)
        time.sleep_ms(150)

        self._cmd(0x11)
        time.sleep_ms(150)

        self._cmd(0x3A)
        self._data(0x55)

        self._cmd(0x36)
        self._data(0x48)

        self._cmd(0x29)
        time.sleep_ms(50)

    def show_logo(self, filename):
        self.set_window(0, 0, self.w - 1, self.h - 1)
    
        self.cs.value(0)
        self.dc.value(1)
    
        with open(filename, "rb") as f:
            while True:
                n = f.readinto(self.buf)
                if not n:
                    break
    
                n &= ~1  # enforce RGB565 alignment
                self.spi.write(self.buf[:n])
    
        self.cs.value(1)

    # -------------------------
    # WINDOW
    # -------------------------
    def set_window(self, x0, y0, x1, y1):
        self._cmd(0x2A)
        self._data(bytearray([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF]))

        self._cmd(0x2B)
        self._data(bytearray([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]))

        self._cmd(0x2C)

    def blit(self, buf, x, y, w, h):
        self.set_window(x, y, x + w - 1, y + h - 1)
    
        self.cs.value(0)
        self.dc.value(1)
        self.spi.write(buf)
        self.cs.value(1)

    # -------------------------
    # DRAW PRIMITIVES
    # -------------------------
    def fill_rect(self, x, y, w, h, color):
        self.set_window(x, y, x + w - 1, y + h - 1)

        hi = color >> 8
        lo = color & 0xFF

        buf = bytearray([hi, lo] * 64)

        pixels = w * h
        self._start()

        while pixels > 0:
            chunk = min(64, pixels)
            self.spi.write(buf[:chunk * 2])
            pixels -= chunk

        self._end()

    def pixel(self, x, y, color):
        self.set_window(x, y, x, y)
        self._start()
        self.spi.write(bytearray([color >> 8, color & 0xFF]))
        self._end()

    def clear(self, color=0x0000):
        self.fill_rect(0, 0, self.w, self.h, color)

    def _draw_glyph_direct(
        self,
        glyph_fb,
        x,
        y,
        gw,
        gh,
        color,
        bg
    ):
        hi = color >> 8
        lo = color & 0xFF
    
        bhi = bg >> 8
        blo = bg & 0xFF
    
        rowbuf = bytearray(gw * 2)
    
        for j in range(gh):
    
            idx = 0
    
            for i in range(gw):
    
                if glyph_fb.pixel(i, j):
                    rowbuf[idx] = hi
                    rowbuf[idx + 1] = lo
                else:
                    rowbuf[idx] = bhi
                    rowbuf[idx + 1] = blo
    
                idx += 2
    
            self.set_window(
                x,
                y + j,
                x + gw - 1,
                y + j
            )
    
            self._start()
            self.spi.write(rowbuf)
            self._end()
                    
    def text(self, x, y, w, h, string, color, bg=0x0000, font_size=30):
        if font_size != 30:
            fbuf = framebuf.FrameBuffer(
                bytearray(w * h * 2),
                w,
                h,
                framebuf.RGB565
            )
        
            fbuf.fill(bg)
        
            # --- safety: clip string to fit width ---
            max_chars = max(1, w // font_size)
            clipped = string[:max_chars]
        
            # --- safety: clip vertically ---
            max_lines = max(1, h // font_size)
        
            y0 = 0
            lines = [clipped[i:i+max_chars] for i in range(0, len(clipped), max_chars)]
        
            for i, line in enumerate(lines):
                if i >= max_lines:
                    break
                fbuf.text(line, 0, y0, color)
                y0 += font_size
        
            self.blit(fbuf, x, y, w, h)
            return

        cx = x
        cy = y
    
        line_h = 30
        space = 2
    
        for ch in string:
    
            if ch == '\n':
                cx = x
                cy += line_h
                continue
    
            glyph_fb, gw, gh = self._get_glyph(ch)
    
            if cx + gw > x + w:
                cx = x
                cy += line_h
    
            if cy + gh > y + h:
                break
    
            self._draw_glyph_direct(
                glyph_fb,
                cx,
                cy,
                gw,
                gh,
                color,
                bg
            )
    
            cx += gw + space

    def line(self, x0, y0, x1, y1, color):
    
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
    
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
    
        err = dx + dy
    
        while True:
    
            self.pixel(x0, y0, color)
    
            if x0 == x1 and y0 == y1:
                break
    
            e2 = 2 * err
    
            if e2 >= dy:
                err += dy
                x0 += sx
    
            if e2 <= dx:
                err += dx
                y0 += sy


MAX_GLYPH_CACHE = 16

FONT_MAP = {
    16: arial16,
    24: arial24,
    30: arial30,
}

class ST7796DisplayPSRAM:
    """
    ST7796 display driver optimized for ESP32-S3 + PSRAM.

    Key design:
    - Full RGB565 framebuffer stored in RAM (PSRAM recommended)
    - All drawing happens in memory (no SPI per primitive)
    - Only dirty regions are flushed to display
    """

    def __init__(
        self,
        width,
        height,
        pin_cs=config.DISPLAY_PIN_CS,
        pin_rst=config.DISPLAY_PIN_RST,
        pin_dc=config.DISPLAY_PIN_DC,
        pin_mosi=config.DISPLAY_PIN_MOSI,
        pin_sck=config.DISPLAY_PIN_SCK,
        pin_miso=config.DISPLAY_PIN_MISO,
        pin_led=config.DISPLAY_PIN_LED,
        spi_id=2,
        baudrate=40_000_000,
    ):
        self.w = width
        self.h = height

        # -------------------------
        # Framebuffer (PSRAM safe)
        # -------------------------
        self.buffer = bytearray(width * height * 2)
        self.fb = framebuf.FrameBuffer(
            self.buffer,
            width,
            height,
            framebuf.RGB565
        )

        # -------------------------
        # Glyph cache
        # -------------------------
        self.glyph_cache = {}

        # -------------------------
        # Dirty region tracking
        # -------------------------
        self._dirty = False
        self._dx0 = width
        self._dy0 = height
        self._dx1 = 0
        self._dy1 = 0

        # -------------------------
        # Hardware setup
        # -------------------------
        self.cs = Pin(pin_cs, Pin.OUT, value=1)
        self.dc = Pin(pin_dc, Pin.OUT, value=1)
        self.rst = Pin(pin_rst, Pin.OUT, value=1)

        self.led = PWM(Pin(pin_led), freq=1000)
        self.led.duty(1023)

        self.spi = SPI(
            spi_id,
            baudrate=baudrate,
            polarity=0,
            phase=0,
            sck=Pin(pin_sck),
            mosi=Pin(pin_mosi),
            miso=Pin(pin_miso),
        )

        self._init_display()

        # self.color_test()

    # =========================================================
    # BACKLIGHT
    # =========================================================

    def set_backlight(self, level):
        """
        Set display backlight brightness.

        Args:
            level (int): 0–100 percent brightness
        """
        level = max(0, min(100, level))
        duty = int(level * 10.23)
        self.led.duty(duty)

    # =========================================================
    # DIRTY REGION HANDLING
    # =========================================================

    def _mark_dirty(self, x, y, w, h):
        self._dirty = True
        self._dx0 = 0
        self._dy0 = 0
        self._dx1 = self.w - 1
        self._dy1 = self.h - 1

    # =========================================================
    # LOW LEVEL INIT
    # =========================================================

    def _cmd(self, c):
        self.cs.value(0)
        self.dc.value(0)
        self.spi.write(bytearray([c]))
        self.cs.value(1)

    def _data(self, d):
        self.cs.value(0)
        self.dc.value(1)
        self.spi.write(bytearray([d]) if isinstance(d, int) else d)
        self.cs.value(1)

    def _reset(self):
        self.rst.value(1)
        time.sleep_ms(50)
        self.rst.value(0)
        time.sleep_ms(100)
        self.rst.value(1)
        time.sleep_ms(150)

    def _init_display(self):
        """
        Basic ST7796 init sequence.
        (Minimal, assumes default panel configuration)
        """
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

    def color_test(self, delay_ms=500):
        """
        Cycles primary colors to verify RGB565 mapping.
    
        Order:
        Red → Green → Blue → White → Black
        """
    
        colors = [
            ("RED",   0xF800),
            ("GREEN", 0x07E0),
            ("BLUE",  0x001F),
            ("WHITE", 0xFFFF),
            ("BLACK", 0x0000),
        ]
    
        for name, color in colors:
            print(f"Testing {name}")
            self.fb.fill(color)
            self._mark_dirty(0, 0, self.w, self.h)
            self.flush()
            time.sleep_ms(delay_ms)

    # =========================================================
    # FRAME FLUSH
    # =========================================================
    def flush(self):
        if not self._dirty:
            return
    
        x0 = self._dx0
        y0 = self._dy0
        x1 = self._dx1
        y1 = self._dy1
    
        w = x1 - x0 + 1
        h = y1 - y0 + 1
    
        self.set_window(x0, y0, x1, y1)
    
        self.cs.value(0)
        self.dc.value(1)
    
        for row in range(h):
            src_y = y0 + row
            offset = (src_y * self.w + x0) * 2
    
            self.spi.write(self.buffer[offset:offset + w * 2])
    
        self.cs.value(1)
    
        self._dirty = False

    def flush_full(self):
        """
        Force full screen refresh (slow, but simple).
        """
        self.set_window(0, 0, self.w - 1, self.h - 1)

        self.cs.value(0)
        self.dc.value(1)
        self.spi.write(self.buffer)
        self.cs.value(1)

        self._dirty = False

    # =========================================================
    # WINDOW CONTROL
    # =========================================================

    def set_window(self, x0, y0, x1, y1):
        """
        Define drawing window on LCD.
        """

        self._cmd(0x2A)
        self._data(bytearray([
            x0 >> 8, x0 & 0xFF,
            x1 >> 8, x1 & 0xFF
        ]))
    
        self._cmd(0x2B)
        self._data(bytearray([
            y0 >> 8, y0 & 0xFF,
            y1 >> 8, y1 & 0xFF
        ]))
        
        self._cmd(0x2C)

    # =========================================================
    # PRIMITIVES (FRAMEBUFFER BASED)
    # =========================================================

    def pixel(self, x, y, color):
        """
        Draw single pixel into framebuffer.
        """
        self.fb.pixel(x, y, color)
        self._mark_dirty(x, y, 1, 1)

    def fill_rect(self, x, y, w, h, color):
        """
        Fill rectangle in framebuffer.
        """
        self.fb.fill_rect(x, y, w, h, color)
        self._mark_dirty(x, y, w, h)

    def line(self, x0, y0, x1, y1, color):
        """
        Draw line using framebuffer primitive.
        """
        self.fb.line(x0, y0, x1, y1, color)

        self._mark_dirty(
            min(x0, x1),
            min(y0, y1),
            abs(x1 - x0) + 1,
            abs(y1 - y0) + 1
        )

    def clear(self, color=0x0000):
        """
        Clear full screen.
        """
        self.fb.fill(color)
        self._dirty = True
        self._dx0 = 0
        self._dy0 = 0
        self._dx1 = self.w - 1
        self._dy1 = self.h - 1

    # =========================================================
    # TEXT RENDERING (GLYPH CACHE)
    # =========================================================

    def _get_glyph(self, ch, font_size):
        key = (font_size, ch)
    
        if key in self.glyph_cache:
            return self.glyph_cache[key]
    
        font = FONT_MAP[font_size]
    
        glyph, gh, gw = font.get_ch(ch)
    
        fb = framebuf.FrameBuffer(
            bytearray(glyph),
            gw,
            gh,
            framebuf.MONO_HLSB
        )
    
        self.glyph_cache[key] = (fb, gw, gh)
    
        return fb, gw, gh

    def text(self, x, y, w, h, string, color, bg=0x0000, font_size=30):
        """
        Draw text into framebuffer.

        Supports:
        - cached 30px glyph rendering
        - fallback small font using framebuf.text
        """
        if font_size == 8:
            self.fb.fill_rect(x, y, w, h, bg)
            self.fb.text(string[:w // font_size], x, y, color)
            self._mark_dirty(x, y, w, h)
            return

        cx, cy = x, y
        line_h = 30
        space = 2

        for ch in string:
            if ch == '\n':
                cx = x
                cy += line_h
                continue

            glyph_fb, gw, gh = self._get_glyph(ch, font_size)

            if cx + gw > x + w:
                cx = x
                cy += line_h

            if cy + gh > y + h:
                break

            for j in range(gh):
                for i in range(gw):
                    c = color if glyph_fb.pixel(i, j) else bg
                    self.fb.pixel(cx + i, cy + j, c)

            cx += gw + space

        self._mark_dirty(x, y, w, h)

    # =========================================================
    # OPTIONAL: BITMAP BLIT
    # =========================================================

    def blit(self, src_fb, x, y):
        """
        Copy framebuffer into main framebuffer.
        """
        self.fb.blit(src_fb, x, y)

        # NOTE: no size metadata available → assume full screen block
        self._mark_dirty(x, y, 10, 10)  # safe fallback