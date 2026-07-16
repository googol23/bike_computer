from widget import Widget
from st7796 import ST7796Display
import mem
from events import EventType

class Hud:
    def __init__(self, display: ST7796Display):
        self.widgets: dict[str,Widget] = {}
        self.display = display

    def add_widget(self, widget: Widget):
        self.widgets[widget.name] = widget

    def handle_touch(self, point: tuple[int,int], event_type: EventType):
        for widget in self.widgets.values():
            if widget.contains_point(point):
                print(f"Passing touched point {point}({event_type}) to  {widget.name}")
                widget.handle_touch(point, event_type)
        
    def render(self):
        for widget in self.widgets.values():
            # mem.usage("HUB: rendering widget: " + widget.name)
            if widget.dirty:
                widget.render(self.display)

