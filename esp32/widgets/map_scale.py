from .widget import Widget


class MapScale(Widget):
    """Displays a map scale using a horizontal ruler and two end ticks."""

    COLOR = 0xFFFF       # White
    BACKGROUND = 0x0000  # Black
    FONT_SIZE = 8

    TICK_HEIGHT = 6
    TEXT_GAP = 3

    def __init__(self, x, y, w, h, value):
        super().__init__("MapScale", x, y, w, h)

        self.value = value  # Kilometres
        self.dirty = True

    def set_scale(self, scale):
        """Update the displayed scale in kilometres."""
        if scale == self.value:
            return

        self.value = scale
        self.dirty = True

    def _format_scale(self):
        """Return a compact human-readable scale label."""
        value = self.value

        if value is None:
            return ""

        if value < 1:
            return "{} m".format(int(round(value * 1000)))

        if int(value) == value:
            return "{} km".format(int(value))

        return "{:.1f} km".format(value)

    def render(self, display):
        if not self.dirty:
            return

        # # Clear the widget area so an old, longer label disappears.
        # display.fill_rect(
        #     self.x,
        #     self.y,
        #     self.w,
        #     self.h,
        #     self.BACKGROUND,
        # )

        label = self._format_scale()

        # Reserve the lower part of the widget for text.
        ruler_y = self.y + self.TICK_HEIGHT
        ruler_x0 = self.x
        ruler_x1 = self.x + self.w - 1

        # Horizontal ruler.
        display.h_line(
            ruler_x0,
            ruler_y,
            self.w,
            self.COLOR,
        )

        # Left and right ticks.
        display.v_line(
            ruler_x0,
            ruler_y - self.TICK_HEIGHT,
            self.TICK_HEIGHT + 1,
            self.COLOR,
        )

        display.v_line(
            ruler_x1,
            ruler_y - self.TICK_HEIGHT,
            self.TICK_HEIGHT + 1,
            self.COLOR,
        )

        text_y = ruler_y + self.TEXT_GAP
        text_h = self.y + self.h - text_y

        if label and text_h > 0:
            text_width = display.text_width(label, self.FONT_SIZE)
            text_x = self.x + max(0, (self.w - text_width) // 2)

            display.text(
                text_x,
                text_y,
                min(text_width, self.w),
                text_h,
                label,
                self.COLOR,
                bg=self.BACKGROUND,
                font_size=self.FONT_SIZE,
            )

        self.dirty = False