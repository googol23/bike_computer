class EventType:
    NONE = 0
    TOUCH = 1
    ALARM = 2
    BUTTON_PRESSED = 3
    CHARGING = 4


class Event:
    __slots__ = (
        "type",
        "x",
        "y",
        "alarm",
        "button",
    )

    def __init__(self):
        self.clear()

    def clear(self):
        self.type = EventType.NONE
        self.x = 0
        self.y = 0
        self.alarm = None
        self.button = 0


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

    def _reserve(self):
        if self.full():
            return None

        event = self._events[self._tail]
        event.clear()

        self._tail = (self._tail + 1) % self._size
        self._count += 1

        return event

    def post_touch(self, x, y):
        event = self._reserve()

        if event is None:
            return False

        event.type = EventType.TOUCH
        event.x = x
        event.y = y

        return True

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
        if self.empty():
            return None

        event = self._events[self._head]

        self._head = (self._head + 1) % self._size
        self._count -= 1

        return event

    def release(self, event):
        event.clear()