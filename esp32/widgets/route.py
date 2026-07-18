from .widget import Widget
from .map_scale import MapScale
from .location import LocationWidget

from gpx.streamer import GPXStreamer
from gpx.utils import distance_2d_m

class RouteWidget(Widget):
    def __init__(
        self,
        name,
        x,
        y,
        w,
        h,
    ):
        super().__init__(name, x, y, w, h)
        self.padding = 10
        self.streamer: GPXStreamer | None = None

        self.location_widget = LocationWidget("location_on_route", 0, 0, 5, 5, 0xFF00)

        self.min_lat = 0
        self.max_lat = 0
        self.min_lon = 0
        self.max_lon = 0

        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self.screen_points: list[tuple[int, int]] = self.project_to_screen()

        scale_width = max(1, w // 4)
        self.map_scale = MapScale(
            x + w - scale_width - 4,
            y + 4,
            scale_width,
            30,
            value=0,
        )

        self.widgets = [
            self.location_widget,
            self.map_scale
        ]

    def set_streamer(self, streamer: GPXStreamer) -> None:
        self.streamer = streamer
        self.project_to_screen()
        self.dirty = True

    def update(self, values) -> None:
        """It receives current (lat, lon)"""
        lat, lon = values

        if not self.screen_points:
            return

        loc_x, loc_y = self.project_point(lat, lon)

        if 0 <= loc_x < self.w and 0 <= loc_y < self.h:
            self.location_widget.update((self.x + loc_x, self.y + loc_y))

            self.dirty = True

    def update_map_scale(self) -> None:
        ruler_width_px = max(1, self.map_scale.w - 1)
    
        ruler_distance_m = (
            ruler_width_px
            * self.meters_per_pixel_x()
        )
    
        self.map_scale.set_scale(ruler_distance_m / 1000.0)
    
    def meters_per_pixel_x(self) -> float:
        lon_range = self.max_lon - self.min_lon
    
        if lon_range <= 0 or self.scale <= 0:
            return 0.0
    
        center_lat = (self.min_lat + self.max_lat) * 0.5
    
        distance_m = distance_2d_m(
            center_lat,
            self.min_lon,
            center_lat,
            self.max_lon,
        )
    
        displayed_pixels = lon_range * self.scale
    
        if displayed_pixels <= 0:
            return 0.0
    
        return distance_m / displayed_pixels
    
    
    def meters_per_pixel_y(self) -> float:
        lat_range = self.max_lat - self.min_lat
    
        if lat_range <= 0 or self.scale <= 0:
            return 0.0
    
        center_lon = (self.min_lon + self.max_lon) * 0.5
    
        distance_m = distance_2d_m(
            self.min_lat,
            center_lon,
            self.max_lat,
            center_lon,
        )
    
        displayed_pixels = lat_range * self.scale
    
        if displayed_pixels <= 0:
            return 0.0
    
        return distance_m / displayed_pixels

    def project_point(self, lat, lon):
        """
        Convert GPS coordinates into widget-local coordinates.
        Returns coordinates relative to the route widget.
        """

        x = (lon - self.min_lon) * self.scale + self.offset_x

        y = self.offset_y + (self.max_lat - lat) * self.scale

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

        self.screen_points = [self.project_point(lat, lon) for lat, lon, _ in pts]

        self.update_map_scale()

        return self.screen_points

    def render(self, display):

        display.fill_rect(self.x, self.y, self.w, self.h, 0x0000)

        for i in range(1, len(self.screen_points)):
            x1, y1 = self.screen_points[i - 1]
            x2, y2 = self.screen_points[i]

            display.line(self.x + x1, self.y + y1, self.x + x2, self.y + y2, 0xFFFFF)

        # The background clear invalidated both child widgets.
        self.location_widget.dirty = True
        self.map_scale.dirty = True
    
        self.location_widget.render(display)
        self.map_scale.render(display)
        
        self.dirty = False
