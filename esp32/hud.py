from widget import Widget
from st7796 import ST7796Display
import mem

class Hud:
    def __init__(self, display: ST7796Display):
        self.widgets: dict[str,Widget] = {}
        self.display = display

    def add_widget(self, widget: Widget):
        self.widgets[widget.name] = widget

    def render(self):
        for widget in self.widgets.values():
            # mem.usage("HUB: rendering widget: " + widget.name)
            if widget.dirty:
                widget.render(self.display)

