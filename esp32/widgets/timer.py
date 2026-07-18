from .widget import Widget
from .area import AreaWidget
from .text import TextWidget
from events import EventType

class TimerWidget(Widget):
    def __init__(self, name, x, y, w, h, value=None, timer=None):
        super().__init__(name, x, y, w, h, value)
        self.values: tuple = (0, 0, 0)

        self._current_hh = 0
        self._current_mm = 0
        self._current_ss = 0

        self.timer = timer if timer is not None else None

        FONT_SIZE = 8
        text_width_pxl = len(name) * FONT_SIZE + 10
        label_width_pxl = text_width_pxl if text_width_pxl < self.w else self.w
        label_x_0 = self.x + (self.w - label_width_pxl) // 2

        self.backg_widget = AreaWidget(
            ("Background " + name), self.x, self.y, self.w, self.h, 0x0000
        )

        self.label_widget = TextWidget(
            ("Label " + name), label_x_0, self.y, label_width_pxl, FONT_SIZE+8, name, 8
        )

        value_y_0 = self.y + FONT_SIZE + 10
        pad_size = 50
        time_x_0 = self.x + ((self.w - pad_size * 3) // 2)
        self.hh_widget = TextWidget(("HH " + name), time_x_0, value_y_0, pad_size, 30, padding=0)
        self.mm_widget = TextWidget(("MM " + name), time_x_0 + pad_size, value_y_0, pad_size, 30, padding=0)
        self.ss_widget = TextWidget(("SS " + name), time_x_0 + pad_size * 2, value_y_0, pad_size, 30, padding=0)

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

    def handle_touch(self, point, event_type):
        if self.timer:
            if event_type == EventType.SINGLE_TAP:
                print("Toggling timer...")
                self.timer.toggle_pause()

    def update(self, values):
        if values is None or len(values) != 3:
            return

        h, m, s = values
        changed = False

        if h != self._current_hh:
            self.hh_widget.text = f"{h:02d}:"
            self.hh_widget.dirty = True
            self._current_hh = h
            changed = True

        if m != self._current_mm:
            self.mm_widget.text = f"{m:02d}:"
            self.mm_widget.dirty = True
            self._current_mm = m
            changed = True

        if s != self._current_ss:
            self.ss_widget.text = f"{s:02d}"
            self.ss_widget.dirty = True
            self._current_ss = s
            changed = True

        if changed:
            self.values = values
            self.dirty = True


class AlarmWidget(Widget):
    def __init__(self, name, x, y, w, h, alarms_manager):
        super().__init__(name, x, y, w, h)

        self.alarms_manager = alarms_manager
        self.current_alarm = None
        self.pending_alarms = []

        self.visible = False
        self.background_color = 0xF800
        self.text_color = 0xFFFF
        self.font_size = 8
        self.padding = 10

    def activate(self, alarm):
        """
        Called only by the event handler when an ALARM event arrives.
        """
        if alarm is None or not alarm.is_active():
            return

        if alarm is self.current_alarm or alarm in self.pending_alarms:
            return

        if self.current_alarm is None:
            self._show(alarm)
        else:
            self.pending_alarms.append(alarm)

    def _show(self, alarm):
        self.current_alarm = alarm
        self.visible = True
        self.dirty = True

    def _show_next(self):
        while self.pending_alarms:
            alarm = self.pending_alarms.pop(0)

            if alarm.is_active():
                self._show(alarm)
                return

        # Nothing pending. Only redraw if something was previously visible.
        if self.current_alarm is not None or self.visible:
            self.current_alarm = None
            self.visible = False
            self.dirty = True

    def update(self, values=None):
        """
        Handles only the currently displayed alarm.

        Alarm triggering is handled by AlarmsManager and _alarms_loop().
        """
        if self.current_alarm is None:
            if self.pending_alarms:
                self._show_next()
            return

        if self.current_alarm.has_expired():
            self.current_alarm.clear()
            self.current_alarm = None
            self.visible = False
            self.dirty = True
            self._show_next()

    def handle_touch(self, point, event_type):
        """
        Dismiss the currently displayed alarm.
        """
        if self.current_alarm is None:
            return

        print("Dismissing alarm:", self.current_alarm.name)

        self.current_alarm.dismiss()
        self.current_alarm = None
        self.visible = False
        self.dirty = True

        self._show_next()

    def render(self, display):
        if not self.dirty:
            return

        display.fill_rect(
            self.x,
            self.y,
            self.w,
            self.h,
            0x0000,
        )

        if self.visible and self.current_alarm is not None:
            # display.fill_rect(
            #     self.x,
            #     self.y,
            #     self.w,
            #     self.h,
            #     self.background_color,
            # )

            message = self.current_alarm.message or self.current_alarm.name

            display.text(
                self.x + self.padding,
                self.y + self.padding,
                self.w - 2 * self.padding,
                self.h - 2 * self.padding,
                message,
                self.text_color,
                font_size=self.font_size,
            )

        self.dirty = False



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

