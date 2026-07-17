from .widget import Widget

class TextWidget(Widget):
    def __init__(self, name, x, y, w, h, text="None", font_size=30):
        super().__init__(name, x, y, w, h)
        self.text = text
        self.font_size = font_size

        self.padding = (self.h - font_size) // 2 if self.h > font_size else 0
        print(name, "using padding ", self.padding)

    def render(self, display):
        display.text(
            self.x + self.padding,
            self.y + self.padding,
            self.w - 2*self.padding,
            self.h - 2*self.padding,
            self.text,
            0xFFFF,
            font_size=self.font_size,
        )
        self.dirty = False
