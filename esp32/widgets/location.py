from .widget import Widget

class LocationWidget(Widget):
    def __init__(self, name, x, y, w, h, color=0xFFFF):
        super().__init__(name, x, y, w, h)
        self.color = color

    def update(self, values):
        """
        It receives display coordinates as input.
        This widget is controled by the reference on whihc is drawn.
        Example: route widget provide the display
            coordinates for location based on current route render
        """
        print(f"Updating {self.name} with {values}")
        self.x, self.y = values
        self.dirty = True

    def render(self, display, icon: str = "circle"):
        if icon == "circle":
            return display.circle(self.x, self.y, self.w, self.color)
        if icon == "triangle down":
            return display.triangle_down(self.x, self.y, self.h, self.color)
