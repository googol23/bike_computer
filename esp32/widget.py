from gpx.utils import rdp, distance_2d_m
from gpx.streamer import GPXStreamer
from gpx.navigation import NavigationStreamer

from arrow_sprites import ArrowSprites

class Widget:
    def __init__(self, name:str, x:int, y:int, w:int, h:int, value=None):
        self.widgets: list = []
        self.name = name

        self.x = x
        self.y = y
        self.w = w
        self.h = h

        self.values: tuple = ()
        self.dirty = True
        self.print()

    def print(self):
        print(f"name={self.name}, x={self.x}, y={self.y}, w={self.w}, h={self.h}")

    def update(self, values):
        if values != self.values:
            self.values = values
            self.dirty = True

    def render(self, display):
        # print(f"rendering widget: {self.name}")

        for widget in self.widgets:
            if widget.dirty:
                # print(f"rendering widget: {widget.name}")
                widget.render(display)
        
        self.dirty = False


class AreaWidget(Widget):
    def __init__(self, name, x, y, w, h, color=0x0000):
        super().__init__(name, x, y, w, h)
        self.color = color

    def render(self, display):
        display.fill_rect(self.x, self.y, self.w, self.h, self.color)
        self.dirty = False

class TextWidget(Widget):
    def __init__(self, name, x, y, w, h, text="None", font_size=30):
        super().__init__(name, x, y, w, h)
        self.text = text
        self.font_size = font_size

    def render(self, display):
        display.fill_rect(self.x, self.y, self.w, self.h, 0x0000)
        display.text(self.x + 4, self.y + 4, self.w, self.h, self.text, 0xFFFF, font_size=self.font_size)
        self.dirty = False


class ValueWidget(Widget):
    def __init__(self, name, x, y, w, h, value=0, label=None, units=None):
        super().__init__(name, x, y, w, h, value)

        self._last_value = value
        self.label = label if label else name
        self.units = units if units else ""

        label_font_size = 8
        padding = 8
        
        label_width_pxl = len(self.label) * label_font_size
        label_width_pxl = label_width_pxl if label_width_pxl < self.w else self.w
        
        # label alignment top-center
        label_x_0 = x + (self.w - label_width_pxl) // 2

        # units alignment top-right
        units_width_pxl = len(units) * label_font_size if units else 0
        units_x_0 = self.x + self.w - units_width_pxl - padding

        # value alignment center-center
        value_x_0 = self.x + padding
        value_y_0 = self.y + label_font_size + padding
        value_width_pxl = self.w - 2*padding - units_width_pxl 
        values_h = h - label_font_size - padding
        
        
        self.backg_widget = AreaWidget(("Background " + name), self.x, self.y, self.w, self.h, 0x0)
        
        self.label_widget = TextWidget(
            ("Label " + name),
            label_x_0,
            self.y,
            label_width_pxl,
            label_font_size,
            self.label,
            8
        )

        self.value_widget = TextWidget(
            ("Value " + name),
            value_x_0,
            value_y_0,
            value_width_pxl,
            values_h,
            f"{self._last_value:.2f}"
        )

        self.units_widget = TextWidget(
            ("Units " + name),
            units_x_0,
            value_y_0,
            units_width_pxl,
            label_font_size,
            self.units,
            8
        )

        self.widgets = [
            self.backg_widget,
            self.label_widget,
            self.value_widget,
            self.units_widget,
        ]
        
        self.formater = None
        
    def format_value(self, value):
        return f"{value:.2f}" if self.formater is None else self.formater(value)

    def set_formater(self, formater):
        self.formater = formater
        self.value_widget.text = self.format_value(self._last_value)
        self.value_widget.dirty = True
        self.dirty = True
        
    def update(self, values):
        super().update(values)

        # Extract value from values tuple updated by superclass
        if self.values and len(self.values) > 0:
            self._last_value = self.values[0]
            self.value_widget.text = self.format_value(self._last_value)
            self.value_widget.dirty = True
            self.dirty = True

    def render(self, display):
        super().render(display)
        
        
class TimerWidget(Widget):
    def __init__(self, name, x, y, w, h, value=None):
        super().__init__(name, x, y, w, h, value)
        self.values: tuple = (0,0,0)

        self._current_hh = 0
        self._current_mm = 0
        self._current_ss = 0
        
        FONT_SIZE = 8
        text_width_pxl = len(name) * FONT_SIZE
        label_width_pxl = text_width_pxl if text_width_pxl < self.w else self.w
        label_x_0 = self.x + (self.w - label_width_pxl) // 2
        
        self.backg_widget = AreaWidget(("Background " + name), self.x, self.y, self.w, self.h, 0x0000)
        
        self.label_widget = TextWidget(("Label " + name),
            label_x_0,
            self.y,
            label_width_pxl,
            FONT_SIZE,
            name,
            8
        )
    
        value_y_0 = self.y + FONT_SIZE + 10
        pad_size = 50
        time_x_0 = self.x + ((self.w - pad_size * 3) // 2)
        self.hh_widget = TextWidget(("HH " + name),
            time_x_0,
            value_y_0,
            pad_size,
            30
        )
        self.mm_widget = TextWidget(("MM " + name),
            time_x_0 + pad_size,
            value_y_0,
            pad_size,
            30
        )
        self.ss_widget = TextWidget(("SS " + name),
            time_x_0 + pad_size*2,
            value_y_0,
            pad_size,
            30
        )

        h, m, s = self.values if len(self.values) == 3 else (0, 0, 0)
        self.hh_widget.text = f"{h:02d}:"
        self.mm_widget.text = f"{m:02d}:"
        self.ss_widget.text = f"{s:02d}"
        
        self.widgets = [
            self.backg_widget,
            self.label_widget,
            self.hh_widget,
            self.mm_widget,
            self.ss_widget,
        ]

    def update(self, values):
        if len(values) == 3:
            h, m, s = values

            if h != self._current_hh:
                self.hh_widget.text = f"{h:02d}:"
                self.hh_widget.dirty = True
                self._current_hh = h

            if m != self._current_mm:
                self.mm_widget.text = f"{m:02d}:"
                self.mm_widget.dirty = True
                self._current_mm = m

            if s != self._current_ss:
                self.ss_widget.text = f"{s:02d}"
                self.ss_widget.dirty = True
                self._current_ss = s

        self.dirty = True
        
class CoordinateWidget(Widget):
    def __init__(self, name, x, y, w, h, value=None):
        super().__init__(name, x, y, w, h, value)
        
    def render(self, display):
        display.fill_rect(self.x, self.y, self.w, self.h, 0x0000)
        
        if len(self.values) < 2:
            text = self.name
        else:
            lat_str = f"{abs(self.values[0]):.4f}{'N' if self.values[0] > 0 else 'S'}"
            lon_str = f"{abs(self.values[1]):.4f}{'E' if self.values[1] > 0 else 'W'}"

            text = f"{lat_str}\n{lon_str} "

        display.text(self.x + 4, self.y + 4, self.w, self.h, text, 0xFFFF)

        self.dirty = False

class LocationWidget(Widget):
    def __init__(self, name, x, y, w, h, color=0xFFFF):
        super().__init__(name, x, y, w, h)
        self.color = color
      

    def update(self, values):
        """
            It receives display coordinates as input.
            This widget is controled by the reference on whihc is drawn.
            Example: route widget provide the display
                coordinates for location based on current route render
        """
        print(f"Updating {self.name} with {values}")
        self.x, self.y = values
        self.dirty = True

    def render(self, display):
        # draw filled circle (ESP32 LCD typical API)
        print(f"Rendering {self.name}")
        # try:
        # print(f"drawing location at {self.x}, {self.y} with radiues")
        r = 6
        display.circle(self.x, self.y, r, self.color)
        # except:
        #     # fallback if only pixel available
        #     for dx in range(-self.w, self.w + 1):
        #         for dy in range(-self.h, self.h + 1):
        #             display.pixel(self.x + dx, self.y + dy, self.color)

            
class ElevationWidget(Widget):
    def __init__(self, name, x, y, w, h):
        super().__init__(name, x, y, w, h)

        self.streamer: GPXStreamer | None = None

    def project_to_screen(self, padding=10):
        if self.streamer is None or self.streamer.gpx_pts is None:
            return []

        screen_points = []
    
        x0, y0, h0 = self.streamer.gpx_pts[0]
    
        length_2d = distance_2d_m(
            self.streamer.gpx_pts[0][0], self.streamer.gpx_pts[0][1],
            self.streamer.gpx_pts[-1][0], self.streamer.gpx_pts[-1][1]
        )
    
        if length_2d == 0:
            return []
    
        min_elevation = min(p[2] for p in self.streamer.gpx_pts)
        max_elevation = max(p[2] for p in self.streamer.gpx_pts)
        elev_range = max_elevation - min_elevation or 1
    
        usable_w = self.w - 2 * padding
        usable_h = self.h - 2 * padding
    
        for i in range(len(self.streamer.gpx_pts)):
            xi, yi, hi = self.streamer.gpx_pts[i]
    
            dist = distance_2d_m(xi, yi, x0, y0)
    
            slope = 0
            if i > 0:
                _, _, hp = self.streamer.gpx_pts[i - 1]
                prev = distance_2d_m(self.streamer.gpx_pts[i - 1][0], self.streamer.gpx_pts[i - 1][1], x0, y0)
                d = max(0.00001, dist - prev)
                slope = (hi - hp) / d
    
            px = self.x + padding + int(dist / length_2d * usable_w)
    
            py = (
                self.y + self.h - padding
                - int((hi - min_elevation) / elev_range * usable_h)
            )
    
            screen_points.append((px, py, slope))
    
        return screen_points

    def slope_to_color(self, slope):
        # negative = white (as you already decided)
        return 0xFFFFFF
        if slope < 0:
            return 0xFFFFFF
    
        # convert to m/km if slope is in meters per meter or similar
        s = slope * 1000  # adjust ONLY if your slope is km-based; remove if already m/km
    
        if s < 50:
            return 0x00FF00  # green (easy)
    
        elif s < 120:
            return 0xFFA500  # orange (medium)
    
        else:
            return 0xFF0000  # red (hard)

    def render(self, display):
        display.fill_rect(self.x, self.y, self.w, self.h, 0x0000)


        if self.streamer is None or len(self.streamer.gpx_pts) < 2:
            return
    
        screen_points = self.project_to_screen()
        
        for i in range(1, len(screen_points)):
            x1, y1, s1 = screen_points[i - 1]
            x2, y2, s2 = screen_points[i]
    
            color = self.slope_to_color((s1 + s2) * 0.5)
    
            display.line(
                x1, y1,
                x2, y2,
                color
            )
    
        self.dirty = False
        
class RouteWidget(Widget):
    def __init__(self, name, x, y, w, h, ):
        super().__init__(name, x, y, w, h)
        self.padding = 10
        self.streamer: GPXStreamer | None = None

        self.location_widget = LocationWidget("location_on_route", 0,0,15,15, 0xFF00)


        self.min_lat = 0
        self.max_lat = 0
        self.min_lon = 0
        self.max_lon = 0

        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self.route_screen_points:list[tuple[int,int]] = self.project_to_screen()

        self.widgets = [self.location_widget]

    def set_streamer(self, streamer: GPXStreamer) -> None:
        self.streamer = streamer
        self.project_to_screen()
        self.dirty = True
        
    def update(self, values) -> None:
        """ It receives current (lat, lon)"""
        lat, lon = values
    
        if not self.route_screen_points:
            return
    
        loc_x, loc_y = self.project_point(lat, lon)
    
        if (
            0 <= loc_x < self.w and
            0 <= loc_y < self.h
        ):
            self.location_widget.update(
                (
                    self.x + loc_x,
                    self.y + loc_y
                )
            )
    
            self.dirty = True

    def project_point(self, lat, lon):
        """
        Convert GPS coordinates into widget-local coordinates.
        Returns coordinates relative to the route widget.
        """
    
        x = (
            (lon - self.min_lon) * self.scale
            + self.offset_x
        )
    
        y = (
            self.offset_y
            + (self.max_lat - lat) * self.scale
        )
    
        return int(x), int(y)

    def project_to_screen(self):
        if (
            self.streamer is None
            or self.streamer.gpx_pts is None
            or len(self.streamer.gpx_pts) < 2
        ):
            return []
    
        pts = self.streamer.gpx_pts
    
        lats = [p[0] for p in pts]
        lons = [p[1] for p in pts]
    
        self.min_lat = min(lats)
        self.max_lat = max(lats)
    
        self.min_lon = min(lons)
        self.max_lon = max(lons)
    
        lat_range = self.max_lat - self.min_lat
        lon_range = self.max_lon - self.min_lon
    
        if lat_range == 0:
            lat_range = 1e-9
    
        if lon_range == 0:
            lon_range = 1e-9
    
        usable_w = self.w - 2 * self.padding
        usable_h = self.h - 2 * self.padding
    
        scale_x = usable_w / lon_range
        scale_y = usable_h / lat_range
    
        self.scale = min(scale_x, scale_y)
    
        route_w = lon_range * self.scale
        route_h = lat_range * self.scale
    
        #
        # Center route in widget
        #
        self.offset_x = (self.w - route_w) * 0.5
        self.offset_y = (self.h - route_h) * 0.5
    
        self.route_screen_points = [
            self.project_point(lat, lon)
            for lat, lon, _ in pts
        ]
    
        return self.route_screen_points

    def render(self, display):
        print(f"Rendering {self.name}")
        display.fill_rect(self.x, self.y, self.w, self.h, 0x0000)

        for i in range(1, len(self.route_screen_points)):
            x1, y1 = self.route_screen_points[i - 1]
            x2, y2 = self.route_screen_points[i]
        
            display.line(
                self.x + x1,
                self.y + y1,
                self.x + x2,
                self.y + y2,
                0xFFFFF
            )
        
        self.location_widget.render(display)
        self.dirty = False


class NavigationInfoWidget(Widget):
    def __init__(self, name, x, y, w, h):
        super().__init__(name, x, y, w, h)

        self.nav_streamer: NavigationStreamer | None = None

        margin = 2
        text_x = self.x + margin
        text_y = self.y + margin
        text_w = self.w - 2*margin
        text_h = self.h // 2

        self.arrow_sprite_x = self.x + self.w // 2 - 64
        self.arrow_sprite_y = self.y + self.h // 2

        self.desc = TextWidget("NavInfo.desc",text_x, text_y, text_w, text_h, "Waiting instructions ...", 24)

        self.widgets = [
            AreaWidget("area", self.x, self.y, self.w, self.h, 0x0),
            self.desc,
        ]
        
    def update(self, values):
        if self.nav_streamer is not None and self.nav_streamer.get_current() is not None:
            self.desc.text = self.nav_streamer.get_current()['desc']
            self.desc.dirty = True
            self.dirty = True
        
    def render(self, display):
        super().render(display)

        sign = self.nav_streamer.get_current()['sign']
        
        arrow = ArrowSprites(display, sign)
        arrow.blit(self.arrow_sprite_x, self.arrow_sprite_y)
                

        

class NavigationWidget(Widget):
    def __init__(self, name, x, y, w, h):
        super().__init__(name, x, y, w, h)

        self.scale = 0.2

        self.streamer: GPXStreamer | None = None
        self.nav_streamer:NavigationStreamer | None = None

        margin = 5

        elevation_panel_x = self.x
        elevation_panel_y = self.y
        elevation_panel_w = self.w
        elevation_panel_h = 60

        route_panel_x = self.x
        route_panel_y = self.y + elevation_panel_h + margin
        route_panel_w = self.w // 2
        route_panel_h = self.h - elevation_panel_h - 2*margin

        nav_info_panel_x = self.x + route_panel_w + margin
        nav_info_panel_y = self.y + elevation_panel_h + margin
        nav_info_panel_w = self.w - route_panel_w - margin
        nav_info_panel_h = route_panel_h


        self.elevation_widget = ElevationWidget("elv", elevation_panel_x, elevation_panel_y, elevation_panel_w, elevation_panel_h)
        self.route_widget = RouteWidget("route", route_panel_x, route_panel_y, route_panel_w, route_panel_h)
        self.nav_info_widget = NavigationInfoWidget("nav_info", nav_info_panel_x, nav_info_panel_y, nav_info_panel_w, nav_info_panel_h)

        self.widgets = [
            self.elevation_widget,
            self.route_widget,
            self.nav_info_widget,
        ]

    def load_route(self, route_name):
        self.streamer = GPXStreamer("routes/" + route_name + ".gpx")
        self.streamer.get_next_d_km(None, None, self.scale)

        self.nav_streamer = self.streamer.stream_navigation()

        self.route_widget.set_streamer(self.streamer)
        self.elevation_widget.streamer = self.streamer
        
        self.nav_info_widget.nav_streamer = self.nav_streamer
        self.nav_info_widget.update(None)

        self.dirty = True

    def update(self, values):
        if values is not None:
            lat, lon = values

            self.route_widget.update((lat,lon))
            
            if self.nav_streamer.update_position(lat, lon):
                print("New navigation instructions: ", self.nav_streamer.get_current())
                self.nav_info_widget.update(None)


            if self.streamer is not None and distance_2d_m(self.streamer.gpx_pts[-1][0], self.streamer.gpx_pts[-1][1], lat, lon) < 1:
                self.streamer.get_next_d_km(lat, lon, self.scale)

                # Force update of screen points for route widget after new gpx section is called
                self.route_widget.project_to_screen()

                self.elevation_widget.dirty = True

            
            self.dirty = True

        

    def render(self, display):
        super().render(display)



def test_route_widget():
    from gpx.streamer import GPXStreamer
    import matplotlib.pyplot as plt
    import asyncio

    scale = 0.5
    
    gnss_sim = GPXStreamer("routes/arheilgen_to_ludwigsturm.gpx")
    gnss_sim.get_next_d_km(None, None,scale)
    
    # w = RouteWidget("route", 20, 20, 320 // 2, 480 // 2)
    w = NavigationWidget("nav", 20,20, 320 // 2, 480 // 2)
    w.load_route("arheilgen_to_ludwigsturm")
    
    w.streamer = gnss_sim
    
    def on_gpx(lat, lon, vel, die):        
        # print(lat, lon, vel)

        w.update((lat,lon))
        

            # plt.figure(figsize=(3.2,4.8))
            # screen_pts = w.route_widget.route_screen_points
            # x = [pts[0] for pts in screen_pts]
            # y = [pts[1] for pts in screen_pts]

            # if len(gnss_sim.gpx_pts) < 2:
            #     print("Arrived")
            #     return
                
            # print(f"Number of points: {len(gnss_sim.gpx_pts)}")
            
            # plt.plot(x, y)
            # plt.gca().invert_yaxis()
            # plt.savefig(f"frames/frame_{gnss_sim.gpx_pts[0][0]}_{gnss_sim.gpx_pts[0][1]}.png", dpi = 100)

            # print("Getting next section")
            # gnss_sim.get_next_d_km(lat, lon, scale)



    async def gnss_sim_loop():
        for i in range(gnss_sim.rcb.n-1):
            lat_0, lon_0, _ = gnss_sim.get_point(i)
            lat_1, lon_1, _ = gnss_sim.get_point(i+1)
    
            for t in range(5):
                
                lat = (lat_1 - lat_0) * t / 5 + lat_0
                lon = (lon_1 - lon_0) * t / 5 + lon_0

                on_gpx(lat, lon, 25, 100)
                          
    
                await asyncio.sleep(0.01)

    asyncio.run(gnss_sim_loop())


if __name__ == "__main__":
    test_route_widget()