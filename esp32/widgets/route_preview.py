from .widget import Widget

class RoutePreviewWidget(Widget):
    def __init__(self, name, x, y, w, h):
        super().__init__(name, x, y, w, h)

        self.route_name = None
        self.route_info = None

        self.background_color = 0x0000
        self.text_color = 0xFFFF
        self.padding = 5
        self.font_size = 16

    def set_route(self, route_name, route_info=None):
        self.route_name = route_name
        self.route_info = route_info
        self.dirty = True

    def clear(self):
        self.route_name = None
        self.route_info = None
        self.dirty = True

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

        if self.route_name is None:
            text = "Select a route"
        else:
            text = self.route_name

            if self.route_info:
                distance = self.route_info.get(
                    "distance_km"
                )

                if distance is not None:
                    text += "\nDistance: {:.1f} km".format(
                        distance
                    )

        display.text(
            self.x + self.padding,
            self.y + self.padding,
            self.w - 2 * self.padding,
            self.h - 2 * self.padding,
            text,
            self.text_color,
            bg=self.background_color,
            font_size=self.font_size,
        )

        self.dirty = False
