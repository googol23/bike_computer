import asyncio
import mem

from ble_gps_server import BLEGPSServer
from hud import Hud
from route import Route
from widget import ValueWidget, CoordinateWidget, TimerWidget, RouteWidget, ElevationWidget, AreaWidget
from gpx_streamer import distance_3d_m, distance_2d_m

import timer

TFT_WIDTH = 320
TFT_HEIGHT = 480

def distance_formater(value):
    if value is None:
        return "N/A"

    if value < 100:
        return f"{value:.2f}"

    if value < 1000:
        return f"{value:.1f}"

    return f"{value:.0f}"

class AppManager:
    def __init__(self, display, charger):
        self.display = display
        self.charger = charger
        
        # BLE
        mem.usage("waking up BLE")
        self.ble = BLEGPSServer()
        self.ble.set_callback(self.on_gpx)
        mem.usage("BLE alive")

        # Route
        self.route = Route()
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
        pad_height = 55
        
        # TIMER
        n_panels = 2
        pad_width = int(0.50*TFT_WIDTH)
        self.hud.add_widget(
            TimerWidget(
                "TIMER",
                margin,
                margin,
                pad_width,
                pad_height,
            )
        )

        # SPEED
        self.hud.add_widget(
            ValueWidget(
                "SPEED",
                2*margin + pad_width,
                margin,
                TFT_WIDTH - 3*margin - pad_width,
                pad_height,
                0,
                "SPEED",
                "km/h"
            )
        )
        
        # AVG. SPEED
        n_panels = 2
        pad_width = (TFT_WIDTH - (n_panels+1) * margin) // n_panels
        self.hud.add_widget(
            ValueWidget(
                "AVG. SPEED",
                margin,
                (pad_height + 2*margin),
                pad_width,
                pad_height,
                0,
                "AVG. SPEED",
                "km/h"
            )
        )

        # DISTANCE
        self.hud.add_widget(
            ValueWidget(
                "DISTANCE",
                2*margin + pad_width,
                (pad_height + 2*margin),
                pad_width,
                pad_height,
                0,
                "DISTANCE",
                "km"
            )
        )
        self.hud.widgets["DISTANCE"].set_formater(distance_formater)


        
        # ROUTE
        pad_width = TFT_WIDTH - 2*margin
        self.hud.add_widget(
            RouteWidget(
                "ROUTE",
                margin,
                2*pad_height + 3*margin,
                pad_width,
                TFT_HEIGHT - 2*pad_height - 4*margin)
        )
        self.hud.widgets["ROUTE"].load_route("arheilgen_to_Bessungen")
        
        self._dirty = True

    # -----------------------------
    # GPX callback
    # -----------------------------
    def on_gpx(self, lat, lon, vel, die):        

        if not self.timer.is_running():
            return
        
        # avoid duplicate points
        if lat == self._last_lat and lon == self._last_lon:
            return

        if self._last_lat is not None and self._last_lon is not None:
            d = distance_2d_m(
                    self._last_lat,
                    self._last_lon,
                    lat,
                    lon
                )
        else:
            d = 0
            
        # ignore GPS noise
        if d > 0.001:
            self._total_distance += d * 0.001

        self._last_lat = lat
        self._last_lon = lon
        self._last_vel = vel
        self._avg_vel = (self._avg_vel * self._n_points + self._last_vel)/ (self._n_points + 1)
        self._n_points += 1


        # self.hud.widgets["LOC"].update((self._last_lat, self._last_lon))
        self.hud.widgets["SPEED"].update((self._last_vel,))
        self.hud.widgets["AVG. SPEED"].update((self._avg_vel,))
        self.hud.widgets["DISTANCE"].update((self._total_distance,))
        self.hud.widgets["ROUTE"].update((self._last_lat,self._last_lon,))

        print(f"Total distance: {self.hud.widgets['DISTANCE'].values}, dirty: {self.hud.widgets['DISTANCE'].dirty}\n")
        print(f"SPEED: {self.hud.widgets['SPEED'].values}, dirty: {self.hud.widgets['SPEED'].dirty}\n")
        print(f"Average speed: {self.hud.widgets['AVG. SPEED'].values}, dirty: {self.hud.widgets['AVG. SPEED'].dirty}\n")
        print(f"ROUTE  dirty: {self.hud.widgets['ROUTE'].dirty}\n")
        print(f"DIR: {die}\n")


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

            self.display.flush()
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
