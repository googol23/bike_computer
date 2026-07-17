import os
from events import EventType

class Widget:
    def __init__(self, name: str, x: int, y: int, w: int, h: int, value=None):
        self.widgets: list = []
        self.name = name

        self.x = x
        self.y = y
        self.w = w
        self.h = h

        self.values: tuple = ()
        self.dirty = True
        self.print()

    def print(self):
        print(f"name={self.name}, x={self.x}, y={self.y}, w={self.w}, h={self.h}")

    def _mark_all_dirty(self):
        self.dirty = True
        for w in self.widgets:
            w._mark_all_dirty()
        
    def contains_point(self, point: tuple[int,int] | None) -> bool:
        if point:
            return self.x <= point[0] <= self.x + self.w and self.y <= point[1] <= self.y + self.h
        return False

    def handle_touch(self, point: tuple[int,int], event_type: EventType | None):
        for w in self.widgets:
            w.handle_touch(point, event_type)

    def update(self, values):
        if values != self.values:
            self.values = values
            self.dirty = True

    def render(self, display):
        # print(f"rendering widget: {self.name}")

        for widget in self.widgets:
            if widget.dirty:
                # print(f"rendering widget: {widget.name}")
                widget.render(display)

        self.dirty = False
