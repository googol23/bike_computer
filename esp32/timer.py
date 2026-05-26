import time


class Timer:
    def __init__(self):
        self._running = False
        self._paused = False
        self._start_time = 0.0
        self._pause_time = 0.0
        self._elapsed = 0.0

    def start(self):
        if self._running:
            return
        self._running = True
        self._paused = False
        self._elapsed = 0.0
        self._start_time = time.time()

    def pause(self):
        if not self._running or self._paused:
            return
        self._pause_time = time.time()
        self._elapsed += self._pause_time - self._start_time
        self._paused = True

    def resume(self):
        if not self._running or not self._paused:
            return
        self._start_time = time.time()
        self._paused = False

    def stop(self):
        if not self._running:
            return
        if not self._paused:
            self._elapsed += time.time() - self._start_time
        self._running = False
        self._paused = False

    def reset(self):
        self._running = False
        self._paused = False
        self._start_time = 0.0
        self._pause_time = 0.0
        self._elapsed = 0.0

    def elapsed(self):
        if not self._running:
            return 0.0

        if self._paused:
            return self._elapsed

        return self._elapsed + (time.time() - self._start_time)

    def elapsed_hms(self):
        total_seconds = int(self.elapsed())
    
        hh = total_seconds // 3600
        mm = (total_seconds % 3600) // 60
        ss = total_seconds % 60
    
        return hh, mm, ss

    def is_running(self):
        return self._running

    def is_paused(self):
        return self._paused