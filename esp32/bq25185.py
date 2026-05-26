# https://www.alldatasheet.com/datasheet-pdf/view/1761651/TI/BQ25185.html
from machine import Pin

class BQ25185:
    def __init__(self, stat_1_pin: int, stat_2_pin: int):
        self.stat_1 = Pin(stat_1_pin, Pin.IN)
        self.stat_2 = Pin(stat_2_pin, Pin.IN)

    def pin_state(self):
        return self.stat_1.value(), self.stat_2.value()

    def is_charging(self):
        return self.stat_1.value() == 1 and self.stat_2.value() == 0

    def is_full(self):
        return self.stat_1.value() == 1 and self.stat_2.value() == 1

    def has_fault(self):
        return self.stat_1.value() == 0 and self.stat_2.value() == 1