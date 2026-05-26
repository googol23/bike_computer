import re

from machine import Pin, SPI
import time

import framebuf
import arial30
from writer import CWriter

MAX_CACHE = 16
# -------------------------
# DISPLAY DRIVER (FAST CORE)
# -------------------------
class ST7796Display:
    def __init__(
        self,
        width,
        height,
        pin_cs=15,
        pin_rst=4,
        pin_dc=2,
        pin_mosi=23,
        pin_sck=18,
        pin_miso=19,
        pin_led=32,
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

        self.led = Pin(pin_led, Pin.OUT, value=1)

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
            fbuf = framebuf.FrameBuffer(bytearray(w * h * 2), w, h, framebuf.RGB565)
            fbuf.fill(bg)
            fbuf.text(string, 0, 0, color)
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