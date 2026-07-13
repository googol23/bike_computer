import time


class Alarm:
    def __init__(self, name: str, period: int, osd_duration: int, message:str | None = None):
        """
        name:
            Alarm identifier, for example "WATER" or "FOOD".

        period:
            Seconds between reminders.

        osd_duration:
            Seconds the reminder remains active on screen.
        """
        if period <= 0:
            raise ValueError("Alarm period must be greater than zero")
    
        if osd_duration <= 0:
            raise ValueError("OSD duration must be greater than zero")

        self.name = name
        self.period = int(period)
        self.osd_duration = int(osd_duration)
        self.message = message

        self._period_ms = self.period * 1000
        self._osd_duration_ms = self.osd_duration * 1000

        self._last_trigger_ms = time.ticks_ms()
        self._active_since_ms = None
        self._enabled = True

    def update(self) -> bool:
        """
        Call regularly.

        Returns True only when the alarm changes from inactive to active.
        """
        if not self._enabled or self.is_active():
            return False

        now = time.ticks_ms()

        if time.ticks_diff(now, self._last_trigger_ms) >= self._period_ms:
            self._active_since_ms = now
            self._last_trigger_ms = now
            return True

        return False

    def is_active(self) -> bool:
        return self._active_since_ms is not None

    def has_expired(self) -> bool:
        """
        Returns True when the on-screen display duration has elapsed.
        """
        if not self.is_active():
            return False

        elapsed = time.ticks_diff(
            time.ticks_ms(),
            self._active_since_ms
        )

        return elapsed >= self._osd_duration_ms

    def dismiss(self):
        """
        Acknowledge and hide the current reminder.
        The next reminder occurs one full period after dismissal.
        """
        self._active_since_ms = None
        self._last_trigger_ms = time.ticks_ms()

    def clear(self):
        """
        Hide the reminder after the OSD timeout.

        Unlike dismiss(), this keeps the original periodic schedule.
        """
        self._active_since_ms = None

    def reset(self):
        """
        Restart the alarm countdown.
        """
        self._active_since_ms = None
        self._last_trigger_ms = time.ticks_ms()

    def enable(self):
        self._enabled = True
        self.reset()

    def disable(self):
        self._enabled = False
        self._active_since_ms = None

    def is_enabled(self) -> bool:
        return self._enabled

    def seconds_remaining(self) -> int:
        if not self._enabled or self.is_active():
            return 0

        elapsed_ms = time.ticks_diff(
            time.ticks_ms(),
            self._last_trigger_ms
        )

        remaining_ms = max(0, self._period_ms - elapsed_ms)
        return (remaining_ms + 999) // 1000

class AlarmsManager:
    def __init__(self, alarms: list[Alarm] | None = None):
        self.alarms: list[Alarm] = alarms if alarms is not None else []

    def add_alarm(self, alarm: Alarm):
        self.alarms.append(alarm)

    def update(self):
        """
        Returns a list containing only newly triggered alarms.
        """
        triggered = []

        for alarm in self.alarms:
            if alarm.update():
                triggered.append(alarm)

        return triggered

    def active_alarms(self):
        return [
            alarm
            for alarm in self.alarms
            if alarm.is_active()
        ]