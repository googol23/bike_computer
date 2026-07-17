from .widget import Widget

class Buttom(Widget):
    def __init__(self, name, x, y, w, h, on_push=None, color=None):
        super().__init__(name, x, y, w, h)
        self.on_push = on_push
        self.color = color if color else 0xFFFF

    def handle_touch(self, point, event_type):
        if not self.contains_point(point):
            return
    
        print(
            "[DEBUG]",
            self.name,
            "pressed at",
            point,
            "bounds:",
            self.x,
            self.y,
            self.w,
            self.h,
        )
    
        if self.on_push is not None:
            self.on_push()


    def render(self, display):
        display.fill_rect(
            self.x,
            self.y,
            self.w,
            self.h,
            self.color,
        )
