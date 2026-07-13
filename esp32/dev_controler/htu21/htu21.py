from machine import I2C, Pin
import time

class HTU21:

    ADDRESS = 0x40

    CMD_TEMP = 0xF3       # No Hold Master
    CMD_HUM = 0xF5
    CMD_RESET = 0xFE

    def __init__(self, scl_pin:int, sda_pin:int, temp_offset=0.0, hum_offset=0.0):
        
        self.i2c = I2C(
            0,
            scl=Pin(scl_pin),
            sda=Pin(sda_pin),
            freq=50000
        )
        self.temp_offset = temp_offset
        self.hum_offset = hum_offset

    def reset(self):
        self.i2c.writeto(self.ADDRESS, b'\xFE')
        time.sleep_ms(20)

    def read_temperature(self):
    
        self.i2c.writeto(self.ADDRESS, b'\xF3')
    
        time.sleep_ms(60)
    
        data = self.i2c.readfrom(self.ADDRESS, 3)
    
        raw = (data[0] << 8) | data[1]
        raw &= 0xFFFC
    
        return -46.85 + 175.72 * raw / 65536 + self.temp_offset

    def read_humidity(self):
    
        self.i2c.writeto(self.ADDRESS, b'\xF5')
    
        time.sleep_ms(20)
    
        data = self.i2c.readfrom(self.ADDRESS, 3)
    
        raw = (data[0] << 8) | data[1]
        raw &= 0xFFFC
    
        rh = -6 + 125.0 * raw / 65536
    
        if rh < 0:
            rh = 0
    
        if rh > 100:
            rh = 100
    
        return rh + self.hum_offset

    def read(self):
        return (
            self.read_temperature(),
            self.read_humidity()
        )
