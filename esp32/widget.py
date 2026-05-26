class Widget:
    def __init__(self, name:str, x:int, y:int, w:int, h:int, value=None):
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

    def update(self, values):
        if values != self.values:
            self.values = values
            self.dirty = True

    def render(self, display):
        print(f"rendering widget: {self.name}")

        for widget in self.widgets:
            if widget.dirty:
                print(f"rendering widget: {widget.name}")
                widget.render(display)
        
        self.dirty = False


class AreaWidget(Widget):
    def __init__(self, name, x, y, w, h, color=0x0000):
        super().__init__(name, x, y, w, h)
        self.color = color

    def render(self, display):
        display.fill_rect(self.x, self.y, self.w, self.h, self.color)
        self.dirty = False

class TextWidget(Widget):
    def __init__(self, name, x, y, w, h, text="None", font_size=30):
        super().__init__(name, x, y, w, h)
        self.text = text
        self.font_size = font_size

    def render(self, display):
        display.text(self.x + 4, self.y + 4, self.w, self.h, self.text, 0xFFFF, font_size=self.font_size)
        self.dirty = False

               
class DistanceWidget(Widget):
    def __init__(self, name, x, y, w, h, value=0):
        super().__init__(name, x, y, w, h, value)
        self.values: tuple = (0,)
        
        FONT_SIZE = 8
        text_width_pxl = len(name) * FONT_SIZE
        label_width_pxl = text_width_pxl if text_width_pxl < w else w
        label_x_0 = x + (w - label_width_pxl) // 2
        value_y_0 = self.y + FONT_SIZE + 10
        units_x_0 = x + int(0.80*w)
        units_wth = int(0.2*w)
        values_h = h - FONT_SIZE - 10
        
        
        self.backg_widget = AreaWidget(("Background " + name), self.x, self.y, self.w, self.h, 0x0000)
        
        self.label_widget = TextWidget(
            ("Label " + name),
            label_x_0,
            self.y,
            label_width_pxl,
            FONT_SIZE,
            name,
            8
        )

        self.value_widget = TextWidget(
            ("Value " + name),
            x+20,
            value_y_0,
            units_x_0,
            values_h,
            str(value)
        )

        self.units_widget = TextWidget(
            ("Units " + name),
            units_x_0,
            value_y_0,
            units_wth,
            values_h,
            "km",
            8
        )        
        
        self.widgets = [
            self.backg_widget,
            self.label_widget,
            self.value_widget,
            self.units_widget
        ]
        

    def update(self, values):
        super().update(values)
        self.value_widget.text = f"{values[0]:.2f}" if values and len(values) > 0 else f"0.00"
        self.value_widget.dirty = True
        self.dirty = True

    def render(self, display):
        super().render(display)

        
class TimerWidget(Widget):
    def __init__(self, name, x, y, w, h, value=None):
        super().__init__(name, x, y, w, h, value)
        self.values: tuple = (0,0,0)
        
        FONT_SIZE = 8
        text_width_pxl = len(name) * FONT_SIZE
        label_width_pxl = text_width_pxl if text_width_pxl < self.w else self.w
        label_x_0 = self.x + (self.w - label_width_pxl) // 2
        
        self.backg_widget = AreaWidget(("Background " + name), self.x, self.y, self.w, self.h, 0x0000)
        
        self.label_widget = TextWidget(("Label " + name),
            label_x_0,
            self.y,
            label_width_pxl,
            FONT_SIZE,
            name,
            8
        )
    
        value_y_0 = self.y + FONT_SIZE + 10
        pad_size = 50
        time_x_0 = self.x + ((self.w - pad_size * 3) // 2)
        self.hh_widget = TextWidget(("HH " + name),
            time_x_0,
            value_y_0,
            pad_size,
            pad_size
        )
        self.mm_widget = TextWidget(("MM " + name),
            time_x_0 + pad_size,
            value_y_0,
            pad_size,
            pad_size
        )
        self.ss_widget = TextWidget(("SS " + name),
            time_x_0 + pad_size*2,
            value_y_0,
            pad_size,
            pad_size
        )

        h, m, s = self.values if len(self.values) == 3 else (0, 0, 0)
        self.hh_widget.text = f"{h:02d}:"
        self.mm_widget.text = f"{m:02d}:"
        self.ss_widget.text = f"{s:02d}"
        
        self.widgets = [
            self.backg_widget,
            self.label_widget,
            self.hh_widget,
            self.mm_widget,
            self.ss_widget,
        ]

        
class CoordinateWidget(Widget):
    def __init__(self, name, x, y, w, h, value=None):
        super().__init__(name, x, y, w, h, value)
        
    def render(self, display):
        display.fill_rect(self.x, self.y, self.w, self.h, 0x0000)
        
        if len(self.values) < 2:
            text = self.name
        else:
            lat_str = f"{abs(self.values[0]):.4f}{'N' if self.values[0] > 0 else 'S'}"
            lon_str = f"{abs(self.values[1]):.4f}{'E' if self.values[1] > 0 else 'W'}"

            text = f"{lat_str}\n{lon_str} "

        display.text(self.x + 4, self.y + 4, self.w, self.h, text, 0xFFFF)

        self.dirty = False

class SpeedWidget(Widget):
    def __init__(self, name, x, y, w, h, value=None):
        super().__init__(name, x, y, w, h, value)
        self.values: tuple = (0,)

        FONT_SIZE = 8
        text_width_pxl = len(name) * FONT_SIZE
        label_width_pxl = text_width_pxl if text_width_pxl < w else w
        label_x_0 = x + (w - label_width_pxl) // 2
        value_y_0 = self.y + FONT_SIZE + 10
        units_x_0 = x + int(0.80*w)
        units_wth = int(0.2*w)
        values_h = h - FONT_SIZE - 10
        
        
        self.backg_widget = AreaWidget(("Background " + name), self.x, self.y, self.w, self.h, 0x0000)
        
        self.label_widget = TextWidget(
            ("Label " + name),
            label_x_0,
            self.y,
            label_width_pxl,
            FONT_SIZE,
            name,
            8
        )

        self.value_widget = TextWidget(
            ("Value " + name),
            x+20,
            value_y_0,
            units_x_0,
            values_h,
            str(value)
        )

        self.units_widget = TextWidget(
            ("Units " + name),
            units_x_0,
            value_y_0,
            units_wth,
            values_h,
            "km/h",
            8
        )        
        
        self.widgets = [
            self.backg_widget,
            self.label_widget,
            self.value_widget,
            self.units_widget
        ]

class SlopeWidget(Widget):
    def __init__(self, name, x, y, w, h, value=None):
        super().__init__(name, x, y, w, h, value)
        
    def render(self, display):
        display.fill_rect(self.x, self.y, self.w, self.h, 0x0000)
        
        if len(self.values) == 0:
            text = self.name
        else:
            text = f"{self.values[0]} %"

        display.text(self.x + 4, self.y + 4, self.w, self.h, text, 0xFFFF)

        self.dirty = False
