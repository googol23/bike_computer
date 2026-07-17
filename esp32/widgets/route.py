from .widget import Widget
from .location import LocationWidget

from gpx.streamer import GPXStreamer

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

        self.widgets = [self.location_widget]

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

        return self.screen_points

    def render(self, display):

        display.fill_rect(self.x, self.y, self.w, self.h, 0x0000)

        for i in range(1, len(self.screen_points)):
            x1, y1 = self.screen_points[i - 1]
            x2, y2 = self.screen_points[i]

            display.line(self.x + x1, self.y + y1, self.x + x2, self.y + y2, 0xFFFFF)

        self.location_widget.render(display)
        self.dirty = False
