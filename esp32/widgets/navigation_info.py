from .widget import Widget
from .text import TextWidget
from .area import AreaWidget

from arrow_sprites import ArrowSprites
from gpx.navigation import NavigationStreamer

class NavigationInfoWidget(Widget):
    ARROW_WIDTH = 128
    ARROW_HEIGHT = 128

    def __init__(self, name, x, y, w, h):
        super().__init__(name, x, y, w, h)

        self.nav_streamer: NavigationStreamer | None = None

        margin = 2

        text_x = self.x + margin
        text_y = self.y + margin
        text_w = self.w - 2 * margin

        # Leave room for the arrow and margins.
        text_h = max(
            0,
            self.h - self.ARROW_HEIGHT - 3 * margin,
        )

        self.arrow_sprite_x = (
            self.x + (self.w - self.ARROW_WIDTH) // 2
        )

        self.arrow_sprite_y = (
            self.y + self.h - self.ARROW_HEIGHT - margin
        )

        self.desc = TextWidget(
            "NavInfo.desc",
            text_x,
            text_y,
            text_w,
            text_h,
            "Waiting instructions ...",
            24
        )

        self.widgets = [
            AreaWidget(
                "area",
                self.x,
                self.y,
                self.w,
                self.h,
                0x0000,
            ),
            self.desc,
        ]

    def update(self, values):
        if (
            self.nav_streamer is not None
            and self.nav_streamer.get_current() is not None
        ):
            self.desc.text = self.nav_streamer.get_current()["desc"]
            self.desc.dirty = True
            self.dirty = True

    def render(self, display):
        super().render(display)

        sign = self.nav_streamer.get_current()["sign"]

        arrow = ArrowSprites(display, sign)
        arrow.blit(self.arrow_sprite_x, self.arrow_sprite_y)


