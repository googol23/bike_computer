from machine import Pin, SPI


class XPT2046:

    CMD_X = 0xD0
    CMD_Y = 0x90

    def __init__(
        self,
        sck_pin,
        mosi_pin,
        miso_pin,
        cs_pin,
        irq_pin,
        width=320,
        height=480,
        spi_id=2,
        baudrate=1_000_000,
        swap_xy=False,
        invert_x=False,
        invert_y=False,
    ):

        self.spi = SPI(
            spi_id,
            baudrate=baudrate,
            polarity=0,
            phase=0,
            sck=Pin(sck_pin),
            mosi=Pin(mosi_pin),
            miso=Pin(miso_pin),
        )

        self.cs = Pin(cs_pin, Pin.OUT, value=1)
        self.irq = Pin(irq_pin, Pin.IN, Pin.PULL_UP)

        self.width = width
        self.height = height

        self.swap_xy = swap_xy
        self.invert_x = invert_x
        self.invert_y = invert_y

        # Default calibration values
        self.raw_x_min = 200
        self.raw_x_max = 3800
        self.raw_y_min = 200
        self.raw_y_max = 3800

    def _read(self, cmd):
        self.cs.off()
        
        tx = bytearray([cmd, 0x00, 0x00])
        rx = bytearray(3)
        
        self.spi.write_readinto(tx, rx)
        
        self.cs.on()
        
        return ((rx[1] << 8) | rx[2]) >> 3

    def touched(self):
        return self.irq is None or self.irq.value() == 0

    def get_raw(self):
        if not self.touched():
            return None

        return (
            self._read(self.CMD_X),
            self._read(self.CMD_Y),
        )

    def get_point(self):
        raw = self.get_raw()

        if raw is None:
            return None

        x, y = raw

        x = (x - self.raw_x_min) * self.width // (self.raw_x_max - self.raw_x_min)
        y = (y - self.raw_y_min) * self.height // (self.raw_y_max - self.raw_y_min)

        x = max(0, min(self.width - 1, x))
        y = max(0, min(self.height - 1, y))

        if self.swap_xy:
            x, y = y, x

        if self.invert_x:
            x = self.width - 1 - x

        if self.invert_y:
            y = self.height - 1 - y

        return (x, y)

    def set_calibration(self, xmin, xmax, ymin, ymax):
        self.raw_x_min = xmin
        self.raw_x_max = xmax
        self.raw_y_min = ymin
        self.raw_y_max = ymax