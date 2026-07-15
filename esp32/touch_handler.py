import time

import settings


class TouchHandler:
    """
    Converts raw touch states into gesture events.

    Supported gestures:
    - single tap
    - double tap
    - long press

    Call update(point) repeatedly from the touch loop.

    point:
        None when the screen is not touched.
        (x, y) while the screen is touched.
    """

    def __init__(self, event_queue):
        self.event_queue = event_queue

        self._is_pressed = False
        self._press_started_ms = 0
        self._press_start_point = None
        self._latest_point = None

        self._long_press_posted = False
        self._gesture_cancelled = False

        # Single taps are kept pending until the double-tap window expires.
        self._pending_tap = False
        self._pending_tap_ms = 0
        self._pending_tap_point = None

    def update(self, point):
        now_ms = time.ticks_ms()

        if point is not None:
            self._handle_pressed(point, now_ms)
        else:
            self._handle_released(now_ms)

        self._post_expired_single_tap(now_ms)

    def _handle_pressed(self, point, now_ms):
        if not self._is_pressed:
            self._start_press(point, now_ms)
            return

        self._latest_point = point

        if self._moved_too_far(
            self._press_start_point,
            point,
        ):
            self._gesture_cancelled = True
            return

        if (
            not self._long_press_posted
            and not self._gesture_cancelled
            and time.ticks_diff(
                now_ms,
                self._press_started_ms,
            ) >= settings.LONG_PRESS_MS
        ):
            self._post_long_press(point)
            self._long_press_posted = True

            # A long press cannot also become a tap.
            self._clear_pending_tap()

    def _start_press(self, point, now_ms):
        self._is_pressed = True
        self._press_started_ms = now_ms
        self._press_start_point = point
        self._latest_point = point

        self._long_press_posted = False
        self._gesture_cancelled = False

    def _handle_released(self, now_ms):
        if not self._is_pressed:
            return

        release_point = (
            self._latest_point
            if self._latest_point is not None
            else self._press_start_point
        )

        should_handle_tap = (
            not self._long_press_posted
            and not self._gesture_cancelled
            and release_point is not None
        )

        if should_handle_tap:
            self._handle_tap(release_point, now_ms)

        self._reset_press()

    def _handle_tap(self, point, now_ms):
        if self._pending_tap:
            tap_interval_ms = time.ticks_diff(
                now_ms,
                self._pending_tap_ms,
            )

            taps_are_close = not self._moved_too_far(
                self._pending_tap_point,
                point,
            )

            if (
                tap_interval_ms
                <= settings.DOUBLE_TAP_INTERVAL_MS
                and taps_are_close
            ):
                self._post_double_tap(point)
                self._clear_pending_tap()
                return

            # Previous pending tap was not part of this gesture.
            self._post_single_tap(self._pending_tap_point)

        self._pending_tap = True
        self._pending_tap_ms = now_ms
        self._pending_tap_point = point

    def _post_expired_single_tap(self, now_ms):
        if not self._pending_tap:
            return

        elapsed_ms = time.ticks_diff(
            now_ms,
            self._pending_tap_ms,
        )

        if elapsed_ms > settings.DOUBLE_TAP_INTERVAL_MS:
            self._post_single_tap(self._pending_tap_point)
            self._clear_pending_tap()

    def _post_single_tap(self, point):
        if point is None:
            return

        posted = self.event_queue.post_single_tap(
            point[0],
            point[1],
        )

        if not posted:
            print("Could not post single-tap event: queue full")

    def _post_double_tap(self, point):
        posted = self.event_queue.post_double_tap(
            point[0],
            point[1],
        )

        if not posted:
            print("Could not post double-tap event: queue full")

    def _post_long_press(self, point):
        posted = self.event_queue.post_long_press(
            point[0],
            point[1],
        )

        if not posted:
            print("Could not post long-press event: queue full")

    def _moved_too_far(self, point_a, point_b):
        if point_a is None or point_b is None:
            return False

        dx = point_b[0] - point_a[0]
        dy = point_b[1] - point_a[1]

        tolerance = settings.TOUCH_MOVE_TOLERANCE_PX

        # Avoid square root calculations.
        return dx * dx + dy * dy > tolerance * tolerance

    def _reset_press(self):
        self._is_pressed = False
        self._press_started_ms = 0
        self._press_start_point = None
        self._latest_point = None

        self._long_press_posted = False
        self._gesture_cancelled = False

    def _clear_pending_tap(self):
        self._pending_tap = False
        self._pending_tap_ms = 0
        self._pending_tap_point = None