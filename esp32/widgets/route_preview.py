import math


from .widget import Widget

from gpx.route_cache import RouteCacheBinary
from gpx.utils import rdp


class RoutePreviewWidget(Widget):
    BACKGROUND_COLOR = 0x0000
    TEXT_COLOR = 0xFFFF
    ROUTE_COLOR = 0xFFFF

    PADDING = 5

    TITLE_FONT_SIZE = 8
    INFO_FONT_SIZE = 16

    # RDP tolerance in display pixels.
    SIMPLIFY_EPSILON_PX = 1.0

    def __init__(
        self,
        name,
        x,
        y,
        w,
        h,
    ):
        super().__init__(name, x, y, w, h)

        self.route_name = None
        self.route_info = None

        # Widget-local projected route points.
        self.preview_points: list[
            tuple[int, int]
        ] = []

        self.background_color = self.BACKGROUND_COLOR
        self.text_color = self.TEXT_COLOR
        self.route_color = self.ROUTE_COLOR

        self.padding = self.PADDING

    def set_route(self, route_name, route_info, cache_path):
        self.route_name = route_name
        self.route_info = route_info
        self.cache_path = cache_path
    
        self._build_preview()
    
        self.dirty = True

    def clear(self):
        self.route_name = None
        self.route_info = None
        self.cache_path = None
    
        self.preview_points.clear()
        self.dirty = True

    def _get_layout(self):
        """
        Return widget-local layout rectangles.

        Information occupies approximately the top third.
        Route preview occupies the bottom two thirds.
        """

        content_x = self.padding
        content_y = self.padding

        content_w = max(
            1,
            self.w - 2 * self.padding,
        )
        content_h = max(
            1,
            self.h - 2 * self.padding,
        )

        info_h = max(
            1,
            content_h // 3,
        )

        preview_gap = self.padding

        preview_x = content_x
        preview_y = content_y + info_h + preview_gap

        preview_w = content_w
        preview_h = max(
            1,
            content_h - info_h - preview_gap,
        )

        return (
            content_x,
            content_y,
            content_w,
            info_h,
            preview_x,
            preview_y,
            preview_w,
            preview_h,
        )

    def _get_route_bounds(self):
        if self.route_info is None:
            return None
    
        min_lat = self.route_info.get("min_lat")
        max_lat = self.route_info.get("max_lat")
        min_lon = self.route_info.get("min_lon")
        max_lon = self.route_info.get("max_lon")
    
        if (
            min_lat is None
            or max_lat is None
            or min_lon is None
            or max_lon is None
        ):
            return None
    
        return (
            min_lat,
            max_lat,
            min_lon,
            max_lon,
        )

    def _build_preview(self):
        self.preview_points.clear()
    
        if not self.cache_path:
            return
    
        route_cache = None
    
        try:
            route_cache = RouteCacheBinary(
                self.cache_path
            )
    
            if route_cache.n <= 0:
                return
    
            self._build_preview_from_cache(
                route_cache
            )
    
        except Exception as e:
            print(
                "Route preview failed:",
                self.route_name,
                e,
            )
    
        finally:
            if route_cache is not None:
                try:
                    route_cache.close()
                except Exception:
                    pass
                    
    def _build_preview_from_cache(self, rcb: RouteCacheBinary):
        """
        Read the complete cached route, project it into the preview
        rectangle and simplify it in display-pixel space.
        """

        if rcb is None or rcb.n <= 0:
            return

        bounds = self._get_route_bounds()

        if bounds is None:
            return

        (
            min_lat,
            max_lat,
            min_lon,
            max_lon,
        ) = bounds

        (
            _,
            _,
            _,
            _,
            preview_x,
            preview_y,
            preview_w,
            preview_h,
        ) = self._get_layout()

        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon

        center_lat = (
            min_lat + max_lat
        ) * 0.5

        # Longitude degrees become physically narrower toward the poles.
        lon_factor = math.cos(
            math.radians(center_lat)
        )

        # Avoid collapse extremely close to the poles.
        if lon_factor < 0.01:
            lon_factor = 0.01

        corrected_lon_range = (
            lon_range * lon_factor
        )

        if lat_range <= 0:
            lat_range = 1e-9

        if corrected_lon_range <= 0:
            corrected_lon_range = 1e-9

        scale_x = (
            preview_w - 1
        ) / corrected_lon_range

        scale_y = (
            preview_h - 1
        ) / lat_range

        scale = min(scale_x, scale_y)

        route_w = corrected_lon_range * scale
        route_h = lat_range * scale

        offset_x = (
            preview_x
            + (preview_w - route_w) * 0.5
        )

        offset_y = (
            preview_y
            + (preview_h - route_h) * 0.5
        )

        projected = []

        for i in range(rcb.n):
            lat_i, lon_i, elevation = rcb.get_point(i)

            lat = lat_i / 1e7
            lon = lon_i / 1e7

            x = (
                offset_x
                + (lon - min_lon)
                * lon_factor
                * scale
            )

            y = (
                offset_y
                + (max_lat - lat)
                * scale
            )

            projected.append(
                (
                    x,
                    y,
                    elevation,
                )
            )

        simplified = rdp(
            projected,
            epsilon=self.SIMPLIFY_EPSILON_PX,
        )

        self.preview_points = [
            (
                int(round(x)),
                int(round(y)),
            )
            for x, y, _ in simplified
        ]

    def _format_distance(self):
        if not self.route_info:
            return "--"

        distance_km = self.route_info.get("distance_km")

        if distance_km is None:
            distance_m = self.route_info.get("distance_m")

            if distance_m is not None:
                distance_km = (
                    distance_m / 1000.0
                )

        if distance_km is None:
            return "--"

        if distance_km < 1:
            return "{} m".format(int(round(distance_km * 1000)))

        return "{:.1f} km".format(distance_km)

    def _format_elevation_gain(self):
        if not self.route_info:
            return "--"

        elevation_gain = self.route_info.get("elevation_gain_m")

        if elevation_gain is None:
            elevation_gain = self.route_info.get("total_ascent_m")

        if elevation_gain is None:
            return "--"

        return f"{int(round(elevation_gain))} m"

    def _render_info(self, display, x, y, w, h):
        if self.route_name is None:
            display.text(
                self.x + x,
                self.y + y,
                w,
                h,
                "Select a route",
                self.text_color,
                bg=self.background_color,
                font_size=self.TITLE_FONT_SIZE,
            )
            return

        title_h = min(
            self.TITLE_FONT_SIZE + 2,
            h,
        )

        display.text(
            self.x + x,
            self.y + y,
            w,
            title_h,
            self.route_name,
            self.text_color,
            bg=self.background_color,
            font_size=self.TITLE_FONT_SIZE,
        )

        info_y = y + title_h + 2
        info_h = h - title_h - 2

        if info_h <= 0:
            return

        info_text = f"Total distance: {self._format_distance()}\nTotal elv gain: {self._format_elevation_gain()}"

        display.text(
            self.x + x,
            self.y + info_y,
            w,
            info_h,
            info_text,
            self.text_color,
            bg=self.background_color,
            font_size=self.INFO_FONT_SIZE,
        )

    def _render_route(self, display):
        if len(self.preview_points) < 2:
            return

        for i in range(1,len(self.preview_points)):
            x1, y1 = self.preview_points[i - 1]
            x2, y2 = self.preview_points[i]

            display.line(
                self.x + x1,
                self.y + y1,
                self.x + x2,
                self.y + y2,
                self.route_color,
            )

    def render(self, display):
        if not self.dirty:
            return

        display.fill_rect(
            self.x,
            self.y,
            self.w,
            self.h,
            self.background_color,
        )

        (
            info_x,
            info_y,
            info_w,
            info_h,
            _,
            _,
            _,
            _,
        ) = self._get_layout()

        self._render_info(
            display,
            info_x,
            info_y,
            info_w,
            info_h,
        )

        self._render_route(display)

        self.dirty = False