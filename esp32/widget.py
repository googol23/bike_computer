from gpx_streamer import GPXStreamReader, distance_2d_m
from navigation import NavigationEngine

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
        self.lat = 0.0
        self.lon = 0.0

        # map bounds (must be set from route or GPS track)
        self.min_lat = 0.0
        self.max_lat = 1.0
        self.min_lon = 0.0
        self.max_lon = 1.0

    def set_bounds(self, min_lat, max_lat, min_lon, max_lon):
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lon = min_lon
        self.max_lon = max_lon

    def update(self, values):
        self.lat, self.lon = values
        self.dirty = True

    def _project(self):
        """lat/lon → screen coordinates inside widget"""
        lat_range = self.max_lat - self.min_lat or 1
        lon_range = self.max_lon - self.min_lon or 1

        x = (self.lon - self.min_lon) / lon_range
        y = (self.lat - self.min_lat) / lat_range

        sx = self.x + int(x * self.w)
        sy = self.y + self.h - int(y * self.h)  # invert Y

        return sx, sy

    def render(self, display):
        sx, sy = self._project()

        # big dot radius
        r = 6

        # draw filled circle (ESP32 LCD typical API)
        try:
            display.fill_circle(sx, sy, r, self.color)
        except:
            # fallback if only pixel available
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if dx * dx + dy * dy <= r * r:
                        display.pixel(sx + dx, sy + dy, self.color)
            
class ElevationWidget(Widget):
    def __init__(self, name, x, y, w, h):
        super().__init__(name, x, y, w, h)

        self.streamer: GPXStreamReader | None = None

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

        self.streamer: GPXStreamReader | None = None


    def project_to_screen(self, padding=10):
        if self.streamer is None or self.streamer.gpx_pts is None:
            print("streamer is None or gpx_pts is None")
            return []

        # print("project_to_screen", self.streamer.gpx_pts)
        pts = self.streamer.rdp()
        lats = [p[0] for p in pts]
        lons = [p[1] for p in pts]

        min_lat = min(lats)
        max_lat = max(lats)

        min_lon = min(lons)
        max_lon = max(lons)

        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon

        # avoid divide-by-zero
        if lat_range == 0:
            lat_range = 1

        if lon_range == 0:
            lon_range = 1

        scale_x = (self.w - 2 * padding) / lon_range
        scale_y = (self.h - 2 * padding) / lat_range

        scale = min(scale_x, scale_y)

        screen_points = []

        for lat, lon, _ in pts:

            x = (lon - min_lon) * scale + padding

            y = self.h - (
                (lat - min_lat) * scale + padding
            )

            screen_points.append(
                (int(x), int(y))
            )

        return screen_points

    def render(self, display):
        super().render(display)
        
        display.fill_rect(self.x, self.y, self.w, self.h, 0x0000)

        if self.streamer is None or len(self.streamer.gpx_pts) < 2:
            return
        
        route_screen_points = self.project_to_screen()
        for i in range(1, len(route_screen_points)):
            x1, y1 = route_screen_points[i - 1]
            x2, y2 = route_screen_points[i]
        
            display.line(
                self.x + x1,
                self.y + y1,
                self.x + x2,
                self.y + y2,
                0xFFFFF
            )
        
        self.dirty = False


class NavigationInfoWidget(Widget):
    def __init__(self, name, x, y, w, h):
        super().__init__(name, x, y, w, h)

        self.nav_engine: NavigationEngine | None = None

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
        self.desc.text = self.nav_engine.current_instruction()['desc']
        self.desc.dirty = True
        self.dirty = True
        
    def render(self, display):
        super().render(display)
        print(self.nav_engine.current_instruction())

        sign = self.nav_engine.current_instruction()['sign']
        
        arrow = ArrowSprites(display, sign)
        arrow.blit(self.arrow_sprite_x, self.arrow_sprite_y)
                
        
        
        

class NavigationWidget(Widget):
    def __init__(self, name, x, y, w, h):
        super().__init__(name, x, y, w, h)

        self.engine = None
        self.scale = 0.2

        self.streamer: GPXStreamReader | None = None

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


        # self.loc_in_route = LocationWidget("loc_in_route", route_panel_x, route_panel_y, route_panel_w, route_panel_h, 0xFF0000)
        # self.loc_in_eleva = LocationWidget("loc_in_eleva", route_panel_x, route_panel_y, route_panel_w, route_panel_h, 0xFF0000)
        self.elevation_widget = ElevationWidget("elv", elevation_panel_x, elevation_panel_y, elevation_panel_w, elevation_panel_h)
        self.route_widget = RouteWidget("route", route_panel_x, route_panel_y, route_panel_w, route_panel_h)
        self.nav_info_widget = NavigationInfoWidget("nav_info", nav_info_panel_x, nav_info_panel_y, nav_info_panel_w, nav_info_panel_h)

        self.widgets = [
            # self.loc_in_route,
            # self.loc_in_eleva,
            self.elevation_widget,
            self.route_widget,
            self.nav_info_widget,
        ]

    def load_route(self, route_name):
        self.streamer = GPXStreamReader("routes/" + route_name + ".gpx")
        self.streamer.next_km(self.scale)
        print(f"len(self.streamer.gpx_pts): {len(self.streamer.gpx_pts)}")
        self.streamer.load_navigation()


        self.route_widget.streamer = self.streamer
        self.elevation_widget.streamer = self.streamer
        
        self.engine = NavigationEngine(self.streamer.nav_pts)
        self.nav_info_widget.nav_engine = self.engine
        self.nav_info_widget.update(None)

        self.dirty = True

    def update(self, values):
        if values is not None:
            lat, lon = values

            if self.engine.update_position(lat, lon):
                print("New navigation instructions")
                self.nav_info_widget.update(None)

            if self.streamer is not None and distance_2d_m(self.streamer.gpx_pts[-1][0], self.streamer.gpx_pts[-1][1], lat, lon) < 1:
                self.streamer.next_km(self.scale)

                self.elevation_widget.dirty = True
                self.route_widget.dirty = True

            
            self.dirty = True

        

    def render(self, display):
        super().render(display)
    