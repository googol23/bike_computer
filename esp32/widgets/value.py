from .widget import Widget
from .area import AreaWidget
from .text import TextWidget

class ValueWidget(Widget):
    def __init__(self, name, x, y, w, h, value=0, label=None, units=None):
        super().__init__(name, x, y, w, h, value)

        self._last_value = value
        self.label = label if label else name
        self.units = units if units else ""

        label_font_size = 8
        padding = 8

        label_width_pxl = len(self.label) * label_font_size + 10
        label_width_pxl = label_width_pxl if label_width_pxl < self.w else self.w

        # label alignment top-center
        label_x_0 = x + (self.w - label_width_pxl) // 2

        # units alignment top-right
        units_width_pxl = len(units) * label_font_size if units else 0
        units_x_0 = self.x + self.w - units_width_pxl - padding

        # value alignment center-center
        value_x_0 = self.x + padding
        value_y_0 = self.y + label_font_size + padding
        value_width_pxl = self.w - 2 * padding - units_width_pxl
        values_h = h - label_font_size - padding

        self.backg_widget = AreaWidget(
            ("Background " + name), self.x, self.y, self.w, self.h, 0x0
        )

        self.label_widget = TextWidget(
            ("Label " + name),
            label_x_0,
            self.y,
            label_width_pxl,
            label_font_size+8,
            self.label,
            8,
        )

        self.value_widget = TextWidget(
            ("Value " + name),
            value_x_0,
            value_y_0,
            value_width_pxl,
            values_h,
            f"{self._last_value:.2f}",
        )

        self.units_widget = TextWidget(
            ("Units " + name),
            units_x_0,
            value_y_0,
            units_width_pxl,
            label_font_size,
            self.units,
            8,
        )

        self.widgets = [
            self.backg_widget,
            self.label_widget,
            self.value_widget,
            self.units_widget,
        ]

        self.formater = None

    def format_value(self, value):
        return f"{value:.2f}" if self.formater is None else self.formater(value)

    def set_formater(self, formater):
        self.formater = formater
        self.value_widget.text = self.format_value(self._last_value)
        self.value_widget.dirty = True
        self.dirty = True

    def update(self, values):
        super().update(values)

        # Extract value from values tuple updated by superclass
        if self.values and len(self.values) > 0:
            self._last_value = self.values[0]
            self.value_widget.text = self.format_value(self._last_value)
            self.value_widget.dirty = True
            self.dirty = True

    def render(self, display):
        super().render(display)
