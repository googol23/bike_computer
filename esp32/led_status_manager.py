from machine import Pin
import neopixel
import uasyncio as asyncio


class LEDState:
    BOOT = "boot"
    INIT = "init"
    WIFI = "wifi"
    READY = "ready"
    ERROR = "error"
    IDLE = "idle"


class LEDStatusManager:
    def __init__(self, pin=48, brightness=0.2):
        self.np = neopixel.NeoPixel(Pin(pin, Pin.OUT), 1)
        self.brightness = brightness

        self.state = LEDState.BOOT
        self._task = None

        # state → behavior config
        self.patterns = {
            LEDState.BOOT:  ("blue",   0.2),
            LEDState.INIT:  ("yellow", 0.3),
            LEDState.WIFI:  ("purple", 0.3),
            LEDState.READY: ("green",  None),
            LEDState.ERROR: ("red",    0.1),
            LEDState.IDLE:  ("white",  3.0),  # heartbeat pulse
        }

    # -------------------------
    # Public API
    # -------------------------
    def set_state(self, state):
        self.state = state

    def start(self):
        if self._task is None:
            self._task = asyncio.create_task(self._runner())

    def stop(self):
        if self._task:
            self._task.cancel()
            self._task = None
        self._off()

    # -------------------------
    # Core loop (non-blocking)
    # -------------------------
    async def _runner(self):
        while True:
            mode = self.state
            color, speed = self.patterns.get(mode, ("white", None))

            if speed is None:
                # SOLID state (e.g. READY)
                self._set_color(color)
                await asyncio.sleep(0.5)
            else:
                # BLINK / PULSE state
                self._set_color(color)
                await asyncio.sleep(speed)
                self._off()
                await asyncio.sleep(speed)

    # -------------------------
    # Hardware helpers
    # -------------------------
    def _scale(self, rgb):
        r, g, b = rgb
        m = self.brightness
        return (int(r * m), int(g * m), int(b * m))

    def _set_color(self, name):
        rgb = self._color_map(name)
        self.np[0] = self._scale(rgb)
        self.np.write()

    def _off(self):
        self.np[0] = (0, 0, 0)
        self.np.write()

    def _color_map(self, name):
        return {
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 180, 0),
            "purple": (160, 0, 255),
            "white": (255, 255, 255),
        }.get(name, (255, 255, 255))