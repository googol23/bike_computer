import asyncio
import time
import mem

from hud import Hud
from gpx.streamer import GPXStreamer
from route import Route
from widget import ValueWidget, TimerWidget, NavigationWidget, AlarmWidget
from alarms import Alarm, AlarmsManager
from gpx.utils import distance_2d_m

from events import EventQueue, Event, EventType
import timer

TFT_WIDTH = 320
TFT_HEIGHT = 480

def distance_formater(value):
    if value is None:
        return "N/A"

    if value < 10:
        return f"{value:.3f}"
        
    if value < 100:
        return f"{value:.2f}"

    if value < 1000:
        return f"{value:.1f}"

    return f"{value:.0f}"

class AppManager:
    def __init__(self, display, charger, gnss_module, sensors, touch_gui = None):
        self.display = display
        self.charger = charger
        self.gnss_module = gnss_module
        self.touch_gui = touch_gui

        self.sensors = sensors

        self.event_queue = EventQueue(size=10)

        # Alarms/Remainders
        self.alarms_manager = AlarmsManager([
            Alarm(
                name = "hydration",
                period = 10,
                osd_duration=8,
                message="Drink Water!"
            ),
            # Alarm(
            #     name = "food",
            #     period = 10,
            #     osd_duration=2,
            #     message="Time for a snack!"
            # )
        ])
        
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
        # HUD layout
        self.hud = Hud(self.display)
        
        margin = 5
        pad_height = 55
        
        alarm_panel_height = pad_height // 2
        alarm_panel_y = TFT_HEIGHT - margin - alarm_panel_height
        
        # TIMER
        n_panels = 2
        pad_width = int(0.50 * TFT_WIDTH)
        
        self.hud.add_widget(
            TimerWidget(
                "TIMER",
                margin,
                margin,
                pad_width,
                pad_height,
                timer=self.timer,
            )
        )
        
        # SPEED
        self.hud.add_widget(
            ValueWidget(
                "SPEED",
                2 * margin + pad_width,
                margin,
                TFT_WIDTH - 3 * margin - pad_width,
                pad_height,
                0,
                "SPEED",
                "km/h",
            )
        )
        
        # AVG. SPEED
        n_panels = 2
        pad_width = (TFT_WIDTH - (n_panels + 1) * margin) // n_panels
        
        self.hud.add_widget(
            ValueWidget(
                "AVG. SPEED",
                margin,
                pad_height + 2 * margin,
                pad_width,
                pad_height,
                0,
                "AVG. SPEED",
                "km/h",
            )
        )
        
        # DISTANCE
        self.hud.add_widget(
            ValueWidget(
                "DISTANCE",
                2 * margin + pad_width,
                pad_height + 2 * margin,
                pad_width,
                pad_height,
                0,
                "DISTANCE",
                "km",
            )
        )
        
        self.hud.widgets["DISTANCE"].set_formater(distance_formater)
        
        # NAVIGATION
        navigation_y = 2 * pad_height + 3 * margin
        navigation_width = TFT_WIDTH - 2 * margin
        
        # Stop above the alarm status panel.
        navigation_height = alarm_panel_y - margin - navigation_y
        
        self.hud.add_widget(
            NavigationWidget(
                "NAVIGATION",
                margin,
                navigation_y,
                navigation_width,
                navigation_height,
            )
        )
        
        self.hud.widgets["NAVIGATION"].load_route(
            "arheilgen_to_ludwigsturm"
        )
        
        # ALARM STATUS PANEL
        self.hud.add_widget(
            AlarmWidget(
                "ALARMS",
                margin,
                alarm_panel_y,
                TFT_WIDTH - 2 * margin,
                alarm_panel_height,
                self.alarms_manager,
            )
        )
        
        self.dirty = True

    # -----------------------------
    # GPX callback
    # -----------------------------
    def on_gpx(self, lat, lon, vel, die):        
        print(lat, lon, vel)
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
        self.hud.widgets["NAVIGATION"].update((self._last_lat,self._last_lon,))

        # print(f"Total distance: {self.hud.widgets['DISTANCE'].values}, dirty: {self.hud.widgets['DISTANCE'].dirty}\n")
        # print(f"SPEED: {self.hud.widgets['SPEED'].values}, dirty: {self.hud.widgets['SPEED'].dirty}\n")
        # print(f"Average speed: {self.hud.widgets['AVG. SPEED'].values}, dirty: {self.hud.widgets['AVG. SPEED'].dirty}\n")
        # print(f"NAVIGATION  dirty: {self.hud.widgets['NAVIGATION'].dirty}\n")
        # print(f"DIR: {die}\n")


        # mark dirty state
        self.dirty = True

    async def _gnss_loop(self):
        while True:
            try:
                fix = self.gnss_module.poll()
        
                if fix and fix["fix"] == 3 and fix["h_acc"] < 50:
                    self.on_gpx(
                        fix["lat"],
                        fix["lon"],
                        fix["speed"],
                        fix["fix"]
                    )
                    print(fix)
                else:
                    print("Waiting for gnss fix...")
            except Exception as e:
                print(e)
    
            await asyncio.sleep(1)   # 1 Hz control
                
    async def gnss_sim_loop(self):
        gnss_sim = GPXStreamer("routes/arheilgen_to_ludwigsturm.gpx")
        for i in range(gnss_sim.rcb.n-1):
            lat_0, lon_0, _ = gnss_sim.get_point(i)
            lat_1, lon_1, _ = gnss_sim.get_point(i+1)

            for t in range(2):
                
                lat = (lat_1 - lat_0) * t / 4 + lat_0
                lon = (lon_1 - lon_0) * t / 4 + lon_0
                
                self.on_gpx(lat,lon, 25, 2)
    
                # await asyncio.sleep(0.01)
    # -----------------------------
    # UI loop (ONLY place rendering happens)
    # -----------------------------
    async def _ui_loop(self):
        last_hms = None
        last_loop_ms = time.ticks_ms()
    
        while True:
            now_ms = time.ticks_ms()
            loop_gap_ms = time.ticks_diff(now_ms, last_loop_ms)
            last_loop_ms = now_ms
    
            if loop_gap_ms > 250:
                print("UI STALL:", loop_gap_ms, "ms")
    
            hms = self.timer.elapsed_hms()
    
            if hms != last_hms:
                last_hms = hms
                self.hud.widgets["TIMER"].update(hms)
    
            self.hud.widgets["ALARMS"].update(None)
            self.hud.render()
    
            flush_ms = self.display.flush()
    
            if flush_ms > 100:
                print("SLOW FLUSH:", flush_ms, "ms")
    
            await asyncio.sleep_ms(20)

    async def _touch_loop(self):
        if self.touch_gui is None:
            return

        was_pressed = False
       
        while True:
            point = self.touch_gui.get_point()
            # print(point)
            is_pressed = point is not None
    
            # Trigger only on the initial press
            if is_pressed and not was_pressed:
                self.event_queue.post_touch(x=point[0], y=point[1])
    
            was_pressed = is_pressed
    
            await asyncio.sleep(0.05)

                
    async def _event_loop(self):
        while True:
            event = self.event_queue.get()
    
            if event is None:
                await asyncio.sleep(0.010)
                continue
    
            try:
                if event.type == EventType.TOUCH:
                    self.hud.touch_point((event.x, event.y))
    
                elif event.type == EventType.ALARM:
                    alarm = event.alarm
    
                    if alarm is not None:
                        print("Handling alarm:", alarm.name)
                        self.hud.widgets["ALARMS"].activate(alarm)
    
                elif event.type == EventType.BUTTON_PRESSED:
                    pass
    
            finally:
                self.event_queue.release(event)
        
    async def _sensor_reading(self):
        while True:
            try:
                t, h = self.sensors[0].read()
                msg = f"DATA: \"temperature\": {t},humidity: {h}\n"
                print(msg)

                # if self.charger.is_charging():
                #     self.event_queue.post_charging()
                    
            except Exception as e:
                pass
                # print(f"Error reading sensor: {e}\n")

            await asyncio.sleep(0.01)

    async def _alarms_loop(self):
        if self.alarms_manager is None:
            return
    
        while True:
            triggered_alarms = self.alarms_manager.update()
    
            for alarm in triggered_alarms:
                if not self.event_queue.post_alarm(alarm):
                    print("Could not post alarm event: queue full")
    
                    # The event was not delivered, so deactivate the alarm.
                    # It can trigger again according to its normal schedule.
                    alarm.clear()
    
            await asyncio.sleep(0.5)


    # -----------------------------
    # run system
    # -----------------------------
    async def run(self):
        self.timer.start()
        
        # asyncio.create_task(self.ble.run())
        asyncio.create_task(self._event_loop())
        asyncio.create_task(self._ui_loop())
        asyncio.create_task(self._touch_loop())
        asyncio.create_task(self._alarms_loop())
        # asyncio.create_task(self._gnss_loop())
        # 
        # asyncio.create_task(self.gnss_sim_loop())
        
        # asyncio.create_task(self._sensor_reading())

        while True:
            await asyncio.sleep(1)

    


        

        
        
