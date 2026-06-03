from machine import Pin
import neopixel
import time

STATE = {
    "BOOT": "blue_blink",
    "INIT_HW": "yellow_blink",
    "WIFI": "purple_blink",
    "OK": "green",
    "ERROR": "red_blink",
    "IDLE": "white_pulse"
}

class OnboardRGB:
    def __init__(self, pin=48, brightness=0.2):
        self.np = neopixel.NeoPixel(Pin(pin, Pin.OUT), 1)
        self.brightness = brightness
        self.off()

    def _scale(self, color):
        r, g, b = color
        m = self.brightness
        return (int(r * m), int(g * m), int(b * m))

    def set(self, r, g, b):
        self.np[0] = self._scale((r, g, b))
        self.np.write()

    def blink(self, color, duration=1):
        

    def red(self):   self.set(255, 0, 0)
    def green(self): self.set(0, 255, 0)
    def blue(self):  self.set(0, 0, 255)
    def white(self): self.set(255, 255, 255)
    def off(self):   self.set(0, 0, 0)