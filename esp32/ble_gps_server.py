import asyncio
import aioble
import bluetooth
from machine import Pin
import struct

class BLEGPSServer:
    def __init__(self, name="ESP32", led_pin=22, adv_interval_ms=250_000):
        print("BLEGPSServer init")

        self.led = Pin(led_pin, Pin.OUT, value=0)

        self.name = name
        self.adv_interval_ms = adv_interval_ms

        self.SERVICE_UUID = bluetooth.UUID("19b10000-e8f2-537e-4f6c-d104768a1214")
        self.GPS_CHAR_UUID = bluetooth.UUID("19b10001-e8f2-537e-4f6c-d104768a1214")

        self.service = aioble.Service(self.SERVICE_UUID)

        self.gps_char = aioble.Characteristic(
            self.service,
            self.GPS_CHAR_UUID,
            read=True,
            write=True,
            notify=True,
            capture=True,
        )

        aioble.register_services(self.service)

        self._callback = None

        self.rx_buffer = ""

        print("BLEGPSServer ready")

    # -----------------------------
    def set_callback(self, fn):
        self._callback = fn

    # -----------------------------
    def _decode_gps(self, data):
        try:
            text = data.decode().strip()
            gnss = text.split(",")
            return gnss
        except:
            return None

    # -----------------------------
    async def _blink(self):
        self.led.value(1)
        await asyncio.sleep(0.1)
        self.led.value(0)

    # -----------------------------
    
    
    async def _gps_task(self):
        while True:
            try:
                _, data = await self.gps_char.written()
    
                if len(data) != 20:
                    print("bad packet size:", len(data))
                    continue
    
                lat, lon, vel, direction, counter = struct.unpack("<ffffI", data)
    
                print(lat, lon, vel, direction, counter)
    
                if self._callback:
                    self._callback([lat, lon, vel, direction])
    
            except Exception as e:
                print("GPS task error:", e)

    # -----------------------------
    async def _ble_task(self):
        while True:
            try:
                connection = await aioble.advertise(
                    self.adv_interval_ms,
                    name=self.name,
                    services=[self.SERVICE_UUID],
                )
    
                print("Connected")
    
                await connection.disconnected()
    
                print("Disconnected")
    
            except Exception as e:
                print("BLE advertise error:", e)
    
            await asyncio.sleep(3)

    # -----------------------------
    async def run(self):
        asyncio.create_task(self._gps_task())
        asyncio.create_task(self._ble_task())

        while True:
            await asyncio.sleep(.1)