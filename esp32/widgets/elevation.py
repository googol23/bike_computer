from .widget import Widget
from .location import LocationWidget

from gpx.streamer import GPXStreamer

class ElevationWidget(Widget):
    def __init__(self, name, x, y, w, h):
        super().__init__(name, x, y, w, h)

        self.streamer: GPXStreamer | None = None

        self.location_widget = LocationWidget(
            "location_on_elevation_profile", 0, 0, 5, 5, 0xFFFF
        )
        self.widgets = [self.location_widget]

        self.min_elv = 0
        self.max_elv = 1
        self.distance = 0
        self.padding = 10
        self.offset_x = self.padding
        self.offset_y = self.padding

        self.screen_points: list[tuple[int, int]] = self.project_to_screen()

    def set_streamer(self, streamer: GPXStreamer) -> None:
        self.streamer = streamer
        self.project_to_screen()
        self.dirty = True

    def update(self, values):
        """It receives lat, lon
        By finding the closes point in route to current location, elv at route is return
        """
        lat, lon = values

        print(f"updating {self.name} with {lat}, {lon}")

        if self.streamer is None:
            return

        # find idx of closest point in route
        idx_closest, lat1, lon1, d2 = self.streamer.closest_segment_endpoint(lat, lon)
        print(lat, lon, idx_closest, lat1, lon1)

        d_at_closest, elv_at_closest = self.streamer.get_elevation_profile()[
            idx_closest
        ]

        local_x, local_y = self.project_point(d_at_closest, elv_at_closest)
        self.location_widget.update(
            (self.x + local_x, self.y + local_y - 2 * self.location_widget.h)
        )

        self.dirty = True

    def project_point(self, d, elv) -> tuple[int, int]:
        """
        Convert elevation and distnace in route into widget-local coordinates.
        Returns coordinates relative to the route widget.
        """
        x = d / self.distance * (self.w - 2 * self.padding) + self.offset_x
        y = (self.max_elv - elv) / (self.max_elv - self.min_elv) * (
            self.h - 2 * self.padding
        ) + self.offset_y

        return int(x), int(y)

    def project_to_screen(self, padding=10):
        if self.streamer is None:
            return []

        # print(f"projecting {self.name}, {self.streamer.rcb.n} points")

        self.screen_points.clear()

        elv_profile = self.streamer.get_elevation_profile()

        self.distance = elv_profile[-1][0]
        self.min_elv = self.streamer.rcb.min_elv
        self.max_elv = self.streamer.rcb.max_elv

        for distance_m, elevation_m in elv_profile:
            # print(distance_m, elevation_m)

            x = (
                (
                    distance_m / self.distance * (self.w - 2 * self.padding)
                    + self.offset_x
                )
                if self.distance
                else 0
            )

            y = (
                (
                    (self.max_elv - elevation_m)
                    / (self.max_elv - self.min_elv)
                    * (self.h - 2 * self.padding)
                    + self.offset_y
                )
                if (self.max_elv - self.min_elv)
                else self.h // 2
            )

            self.screen_points.append((int(x), int(y)))


        filtered = [self.screen_points[0]]
        for x, y in self.screen_points[1:]:
            px, py = filtered[-1]

            if abs(x - px) >= 3 or abs(y - py) >= 3:
                filtered.append((x, y))
        self.screen_points = filtered

        print(f"Total number of points elevation profile{len(self.screen_points)}")

        return self.screen_points

    def slope_to_color(self, slope):
        # negative = white (as you already decided)
        return 0xFFFFFF
        if slope < 0:
            return 0xFFFFFF

        # convert to m/km if slope is in meters per meter or similar
        s = (
            slope * 1000
        )  # adjust ONLY if your slope is km-based; remove if already m/km

        if s < 50:
            return 0x00FF00  # green (easy)

        elif s < 120:
            return 0xFFA500  # orange (medium)

        else:
            return 0xFF0000  # red (hard)

    def render(self, display):
        print(f"Rendering {self.name}: {len(self.screen_points)}")
        display.fill_rect(self.x, self.y, self.w, self.h, 0x0000)

        if len(self.screen_points) < 2:
            return

        for i in range(1, len(self.screen_points)):
            x1, y1 = self.screen_points[i - 1]
            x2, y2 = self.screen_points[i]
            # print(i, x1, y1, x2, y2)

            if x1 == x2 and y1 == y2:
                continue

            display.line(self.x + x1, self.y + y1, self.x + x2, self.y + y2, 0xFFFFF)

        print(f"buffer fillled")
        self.location_widget.render(display, "triangle down")

        self.dirty = False
