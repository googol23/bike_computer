import sys
import asyncio
import aioble
import bluetooth
import struct
import mem

SERVICE_UUID = bluetooth.UUID("19b10000-e8f2-537e-4f6c-d104768a1214")
GPS_CHAR_UUID = bluetooth.UUID("19b10001-e8f2-537e-4f6c-d104768a1214")

# prof = mem.MemProfiler("BLE")
class BLEGPSServer:
    def __init__(self, name="ESP32", adv_interval_ms=250_000):
        print("BLEGPSServer init")

        self.name = name
        self.adv_interval_ms = adv_interval_ms
        self.lat = None
        self.lon = None
        self.vel = None
        self.direction = None
        self.counter = 0


        self.service = aioble.Service(SERVICE_UUID)

        self.gps_char = aioble.Characteristic(
            self.service,
            GPS_CHAR_UUID,
            read=True,
            write=True,
            notify=True,
            capture=True,
        )

        aioble.register_services(self.service)

        self._callback = None

        print("BLEGPSServer ready")

    # -----------------------------
    def set_callback(self, fn):
        self._callback = fn

    
    async def _gps_task(self):
        while True:
            try:
                event = await self.gps_char.written()
                # print("event:", event)
                
                if isinstance(event, tuple) or isinstance(event, list):
                    data = event[-1]
                else:
                    data = event
    
                if len(data) != 20:
                    # print("bad packet size:", len(data))
                    continue
    
                self.lat, self.lon, self.vel, self.direction, self.counter = struct.unpack("<ffffI", data)
    
                # print("Received:", self.lat, self.lon, self.vel, self.direction, self.counter)
    
                if self._callback:
                    self._callback(self.lat, self.lon, self.vel, self.direction)
    
            except Exception as e:
                sys.print_exception(e)

    # -----------------------------
    async def _ble_task(self):
        while True:
            try:
                connection = await aioble.advertise(
                    self.adv_interval_ms,
                    name=self.name,
                    services=[SERVICE_UUID],
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
            # prof.snapshot()
            await asyncio.sleep(.1)

