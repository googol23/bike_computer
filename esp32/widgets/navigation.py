
from .widget import Widget
from .elevation import ElevationWidget
from .route import RouteWidget
from .navigation_info import NavigationInfoWidget
from .route_list import RouteListWidget


from gpx.navigation import NavigationStreamer
from gpx.streamer import GPXStreamer
from gpx.utils import distance_2d_m

from events import EventType


class NavigationWidget(Widget):
    ROUTE_SCALES_KM = (0.05, 0.1, 0.5)

    def __init__(self, name, x, y, w, h):
        super().__init__(name, x, y, w, h)

        self.scale_index = 0
        self.scale = self.ROUTE_SCALES_KM[self.scale_index]

        self.last_lat = None
        self.last_lon = None

        self.streamer: GPXStreamer | None = None
        self.nav_streamer: NavigationStreamer | None = None

        margin = 5

        elevation_panel_x = self.x
        elevation_panel_y = self.y
        elevation_panel_w = self.w
        elevation_panel_h = 60

        route_panel_x = self.x
        route_panel_y = self.y + elevation_panel_h + margin
        route_panel_w = self.w // 2
        route_panel_h = self.h - elevation_panel_h - 2 * margin

        nav_info_panel_x = self.x + route_panel_w + margin
        nav_info_panel_y = self.y + elevation_panel_h + margin
        nav_info_panel_w = self.w - route_panel_w - margin
        nav_info_panel_h = route_panel_h

        self.elevation_widget = ElevationWidget(
            "elv",
            elevation_panel_x,
            elevation_panel_y,
            elevation_panel_w,
            elevation_panel_h,
        )

        self.route_widget = RouteWidget(
            "route", route_panel_x, route_panel_y, route_panel_w, route_panel_h
        )

        self.nav_info_widget = NavigationInfoWidget(
            "nav_info",
            nav_info_panel_x,
            nav_info_panel_y,
            nav_info_panel_w,
            nav_info_panel_h,
        )

        self.widgets = [
            self.elevation_widget,
            self.route_widget,
            self.nav_info_widget,
        ]

        # Ensure the area is clear at least the very first the widget is drawn
        # or whenever the area is reaused by childern
        self.clear_before_render = True

        self.route_list = RouteListWidget("Route list", x, y, w, h)

    def handle_touch(
        self,
        point: tuple[int, int],
        event_type: EventType | None,
    ):
        if event_type == EventType.LONG_PRESS:
            self.route_list.toggle()
    
            print(
                "RouteList visibility changed to",
                self.route_list.visible,
            )
    
            if self.route_list.visible:
                self.dirty = True
                self.route_list._mark_all_dirty()
            else:
                print("Redrawing navigation after closing route list")
                self._mark_all_dirty()
                self.clear_before_render = True
    
            return
    
        if self.route_list.visible:
            print("Passing touch to route list")
            self.route_list.handle_touch(point, event_type)
    
            if self.route_list.dirty:
                self.dirty = True
    
            return
    
        if (
            event_type == EventType.SINGLE_TAP
            and self.route_widget.contains_point(point)
        ):
            self.scale_index = (
                self.scale_index + 1
            ) % len(self.ROUTE_SCALES_KM)
    
            self.scale = self.ROUTE_SCALES_KM[
                self.scale_index
            ]
    
            print(
                "Route scale changed to:",
                int(self.scale * 1000),
                "m",
            )
    
            self._reload_visible_route()


    def load_route(self, route_name):
        self.streamer = GPXStreamer("routes/" + route_name + ".gpx")
        self.streamer.get_next_d_km(None, None, self.scale)

        self.nav_streamer = self.streamer.stream_navigation()

        self.route_widget.set_streamer(self.streamer)
        self.elevation_widget.set_streamer(self.streamer)

        self.nav_info_widget.nav_streamer = self.nav_streamer
        self.nav_info_widget.update(None)

        self.dirty = True

    def _reload_visible_route(self):
        if self.streamer is None:
            return

        # Use the latest GNSS position. Before the first GNSS update,
        # get_next_d_km() starts from the beginning of the route.
        self.streamer.get_next_d_km(
            self.last_lat,
            self.last_lon,
            self.scale,
        )

        self.route_widget.project_to_screen()
        self.elevation_widget.project_to_screen()

        if self.last_lat is not None and self.last_lon is not None:
            self.route_widget.update((self.last_lat, self.last_lon))
            self.elevation_widget.update((self.last_lat, self.last_lon))

        self.route_widget.dirty = True
        self.elevation_widget.dirty = True
        self.dirty = True

    def update(self, values):
        if values is None:
            return
    
        lat, lon = values
    
        self.last_lat = lat
        self.last_lon = lon
    
        self.route_widget.update((lat, lon))
        self.elevation_widget.update((lat, lon))
    
        if (
            self.nav_streamer is not None
            and self.nav_streamer.update_position(lat, lon)
        ):
            print(
                "New navigation instructions:",
                self.nav_streamer.get_current(),
            )
            self.nav_info_widget.update(None)
    
        if (
            self.streamer is not None
            and self.streamer.gpx_pts
            and distance_2d_m(
                self.streamer.gpx_pts[-1][0],
                self.streamer.gpx_pts[-1][1],
                lat,
                lon,
            ) < 1
        ):
            self.streamer.get_next_d_km(
                lat,
                lon,
                self.scale,
            )
    
            self.route_widget.project_to_screen()
            self.elevation_widget.project_to_screen()
    
            self.route_widget.update((lat, lon))
            self.elevation_widget.update((lat, lon))
    
        self.dirty = True

    def render(self, display):
        if self.route_list.visible:
            return self.route_list.render(display)

        if self.clear_before_render:
            print("Clearing navigation widget background")
    
            display.fill_rect(
                self.x,
                self.y,
                self.w,
                self.h,
                0xFFFF,
            )
    
            self.clear_before_render = False

        super().render(display)
