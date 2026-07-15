import time
import settings

class EventType:
    NONE = 0
    SINGLE_TAP = 1
    DOUBLE_TAP = 2
    LONG_PRESS = 3
    ALARM = 4
    BUTTON_PRESSED = 5
    CHARGING = 6


class Event:
    __slots__ = (
        "type",
        "x",
        "y",
        "alarm",
        "button",
        "posted_ms",
    )

    def __init__(self):
        self.clear()

    def clear(self):
        self.type = EventType.NONE
        self.x = 0
        self.y = 0
        self.alarm = None
        self.button = 0
        self.posted_ms = 0


class EventQueue:
    def __init__(self, size=16):
        if size < 1:
            raise ValueError("Queue size must be greater than zero")

        self._events = [Event() for _ in range(size)]
        self._size = size
        self._head = 0
        self._tail = 0
        self._count = 0

    def empty(self):
        return self._count == 0

    def full(self):
        return self._count >= self._size

    def count(self):
        return self._count

    def _max_age_ms(self, event):
        if event.type in (
            EventType.SINGLE_TAP,
            EventType.DOUBLE_TAP,
            EventType.LONG_PRESS,
        ):
            return settings.TOUCH_EVENT_MAX_AGE_MS
    
        if event.type == EventType.BUTTON_PRESSED:
            return settings.BUTTON_EVENT_MAX_AGE_MS
    
        if event.type == EventType.ALARM:
            return settings.ALARM_EVENT_MAX_AGE_MS
    
        if event.type == EventType.CHARGING:
            return settings.CHARGING_EVENT_MAX_AGE_MS
    
        return None
    
    
    def _expired(self, event, now_ms):
        max_age_ms = self._max_age_ms(event)
    
        if max_age_ms is None:
            return False
    
        age_ms = time.ticks_diff(
            now_ms,
            event.posted_ms,
        )
    
        return age_ms > max_age_ms

    def _reserve(self):
        if self.full():
            return None
    
        event = self._events[self._tail]
        event.clear()
        event.posted_ms = time.ticks_ms()
    
        self._tail = (self._tail + 1) % self._size
        self._count += 1
    
        return event

    def post_touch(self, event_type, x, y):
        event = self._reserve()

        if event is None:
            return False

        event.type = event_type
        event.x = x
        event.y = y

        return True

    def post_single_tap(self, x, y):
        return self.post_touch(
            EventType.SINGLE_TAP,
            x,
            y,
        )
    
    
    def post_double_tap(self, x, y):
        return self.post_touch(
            EventType.DOUBLE_TAP,
            x,
            y,
        )
    
    
    def post_long_press(self, x, y):
        return self.post_touch(
            EventType.LONG_PRESS,
            x,
            y,
        )

    def post_alarm(self, alarm):
        event = self._reserve()

        if event is None:
            return False

        event.type = EventType.ALARM
        event.alarm = alarm

        return True

    def post_button(self, button):
        event = self._reserve()

        if event is None:
            return False

        event.type = EventType.BUTTON_PRESSED
        event.button = button

        return True

    def post_charging(self):
        event = self._reserve()

        if event is None:
            return False

        event.type = EventType.CHARGING

        return True
        
    def get(self):
        now_ms = time.ticks_ms()
    
        while not self.empty():
            event = self._events[self._head]
    
            self._head = (self._head + 1) % self._size
            self._count -= 1
    
            if self._expired(event, now_ms):
                print(
                    "Dropping stale event:",
                    event.type,
                    "age:",
                    time.ticks_diff(now_ms, event.posted_ms),
                    "ms",
                )
    
                event.clear()
                continue
    
            return event
    
        return None

    def release(self, event):
        event.clear()