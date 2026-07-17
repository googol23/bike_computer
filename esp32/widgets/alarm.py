from .widget import Widget

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
