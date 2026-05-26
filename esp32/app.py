import asyncio
import time
import mem

from ble_gps_server import BLEGPSServer
from hud import Hud
from st7796 import ST7796Display
from track import Track
from widget import SlopeWidget, SpeedWidget, CoordinateWidget, TimerWidget, DistanceWidget

import timer

TFT_WIDTH = 320
TFT_HEIGHT = 480

from math import radians, sin, cos, sqrt, atan2

EARTH_RADIUS = 6371000  # meters

def distance_m(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0
    
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat * 0.5) ** 2 +
        cos(lat1) * cos(lat2) *
        sin(dlon * 0.5) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return EARTH_RADIUS * c

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
        self._last_lat = None
        self._last_lon = None
        self._last_vel = None
        self._last_dir = None
        self._avg_vel = 0
        self._total_distance = 0
        self._n_points = 0

        self.timer = timer.Timer()

        # HUD
        self.hud = Hud(self.display)

        margin = 5
        pad_height = 60
        
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

        if not self.timer.is_running():
            return
        
        # avoid duplicate points
        lat = float(gnss[0])
        lon = float(gnss[1])
        vel = float(gnss[2])
        die = float(gnss[3])
        if lat == self._last_lat and lon == self._last_lon:
            return

        d = distance_m(
                self._last_lat,
                self._last_lon,
                lat,
                lon
            )
        # ignore GPS noise
        if d > 2:
            self._total_distance += 0.001*d

        self._last_lat = lat
        self._last_lon = lon
        self._last_vel = vel
        self._avg_vel = (self._avg_vel * self._n_points + self._last_vel)/ (self._n_points + 1)
        self._n_points += 1


        # self.hud.widgets["LOC"].update((self._last_lat, self._last_lon))
        self.hud.widgets["SPEED"].update((self._last_vel,))
        self.hud.widgets["AVG. SPEED"].update((self._avg_vel,))
        self.hud.widgets["DISTANCE"].update((self._total_distance,))

        print(f"Total distance: {self.hud.widgets["DISTANCE"].values}, dirty: {self.hud.widgets["DISTANCE"].dirty}\n")
        print(f"SPEED: {self.hud.widgets["SPEED"].values}, dirty: {self.hud.widgets["SPEED"].dirty}\n")
        print(f"Average speed: {self.hud.widgets["AVG. SPEED"].values}, dirty: {self.hud.widgets["AVG. SPEED"].dirty}\n")
        print(f"DIR: {die}\n")

        self.track.add_point(lat, lon)

        # mark dirty state
        self._dirty = True

    # -----------------------------
    # UI loop (ONLY place rendering happens)
    # -----------------------------
    async def _ui_loop(self):
        while True:
            self.hud.widgets["TIMER"].update(self.timer.elapsed_hms())
            
            self.hud.render()
            # if self._dirty:
                # self._dirty = False

            if self.charger.is_charging():
                pass
                
            await asyncio.sleep(0.01)

    # -----------------------------
    # run system
    # -----------------------------
    async def run(self):
        self.timer.start()
        
        asyncio.create_task(self.ble.run())
        asyncio.create_task(self._ui_loop())

        while True:
            await asyncio.sleep(1)
