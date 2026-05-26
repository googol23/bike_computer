import asyncio
import time
import mem

from ble_gps_server import BLEGPSServer
from hud import Hud
from st7796 import ST7796Display
from track import Track
from widget import SlopeWidget, SpeedWidget, CoordinateWidget, TimerWidget, DistanceWidget


TFT_WIDTH = 320
TFT_HEIGHT = 480


class AppManager:
    def __init__(self, display, charger):
        self.display = display
        self.charger = charger
        
        # BLE
        self.ble = BLEGPSServer()
        self.ble.set_callback(self.on_gpx)
        # mem.usage("BLE INIT")

        # track
        self.track = Track()
        self._last_lat = -1
        self._last_lon = -1
        self._last_vel = -1
        self._last_dir = -1
        self._avg_vel = 0
        self._total_distance = 0
        self._timer = 0

        # HUD
        self.hud = Hud(self.display)

        margin = 5
        pad_height = 80
        
        n_panels = 1
        pad_width = (TFT_WIDTH - (n_panels+1) * margin) // n_panels
        self.hud.add_widget(
            TimerWidget(
                "TIMER",
                margin,
                margin,
                pad_width,
                pad_height,
            )
        )
        
        n_panels = 1
        pad_width = (TFT_WIDTH - (n_panels+1) * margin) // n_panels
        self.hud.add_widget(
            SpeedWidget(
                "SPEED",
                margin,
                pad_height + margin,
                pad_width,
                pad_height,
                0
            )
        )
        
        n_panels = 2
        pad_width = (TFT_WIDTH - (n_panels+1) * margin) // n_panels
        self.hud.add_widget(
            SpeedWidget(
                "AVG. SPEED",
                margin,
                2*(pad_height + margin),
                pad_width,
                pad_height,
                0
            )
        )
        

        self.hud.add_widget(
            DistanceWidget(
                "DISTANCE",
                2*margin + pad_width,
                2*(pad_height + margin),
                pad_width,
                pad_height)
        )
        # mem.usage("HUD CONFIG")


        self._dirty = True

    # -----------------------------
    # GPX callback
    # -----------------------------
    def on_gpx(self, gnss):
        if gnss is None:
            return

        # avoid duplicate points
        lat = float(gnss[0])
        lon = float(gnss[1])
        vel = float(gnss[2])
        die = float(gnss[3])
        if lat == self._last_lat and lon == self._last_lon:
            return

        self._total_distance += ((lat - self._last_lat)**2 + (lon - self._last_lon)**2)**0.5
        self._last_lat = lat
        self._last_lon = lon
        self._last_vel = vel
        self._avg_vel += self._total_distance / self._timer if self._timer > 0 else 0

        print(f"Total distance: {self._total_distance}\n")
        print(f"Average speed: {self._avg_vel}\n")
        print(f"SPEED: {self._last_vel}\n")
        print(f"DIR: {die}\n")
        print(f"TIMER: {self._timer}\n")

        # self.hud.widgets["LOC"].update((self._last_lat, self._last_lon))
        self.hud.widgets["SPEED"].update((self._last_vel,))
        self.hud.widgets["AVG. SPEED"].update((self._avg_vel,))
        self.hud.widgets["DISTANCE"].update((self._total_distance,))

        self.track.add_point(lat, lon)

        # mark dirty state
        self._dirty = True

    # -----------------------------
    # UI loop (ONLY place rendering happens)
    # -----------------------------
    async def _ui_loop(self):
        while True:
            if self._dirty:
                self.hud.render()
                self._dirty = False

            if self.charger.is_charging():
                pass
                
            await asyncio.sleep(0.01)

    # -----------------------------
    # run system
    # -----------------------------
    async def run(self):
        asyncio.create_task(self.ble.run())
        asyncio.create_task(self._ui_loop())

        while True:
            await asyncio.sleep(1)
