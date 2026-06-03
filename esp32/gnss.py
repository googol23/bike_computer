from machine import UART
import time

UBX_SYNC_1 = 0xB5
UBX_SYNC_2 = 0x62

NAV_PVT_CLASS = 0x01
NAV_PVT_ID = 0x07


class GNSSModule:
    def __init__(self, tx, rx, baud=115200):
        self.uart = UART(2, baudrate=baud, tx=tx, rx=rx)

        self.buf = bytearray()
        self.last_fix = None

    # -----------------------------
    # I/O helpers
    # -----------------------------
    def print(self):
        print(f"LAT: {self.last_fix.lat}, LON: {self.last_fix.lon}, SPEED: {self.last_fix.speed}, FIX: {self.last_fix.fix}")

    # -----------------------------
    # UART DRAIN (SAFE + SIMPLE)
    # -----------------------------
    def _fill(self):
        data = self.uart.read()
        if data:
            self.buf.extend(data)

        # safety cap (prevents runaway memory growth)
        if len(self.buf) > 4096:
            self.buf = self.buf[-2048:]

    # -----------------------------
    # UBX CHECKSUM
    # -----------------------------
    def _ck(self, data):
        a = 0
        b = 0
        for c in data:
            a = (a + c) & 0xFF
            b = (b + a) & 0xFF
        return a, b

    # -----------------------------
    # SAFE BUFFER SCAN
    # -----------------------------
    def _process(self):
        i = 0

        while i + 6 <= len(self.buf):

            # sync search
            if self.buf[i] != UBX_SYNC_1 or self.buf[i + 1] != UBX_SYNC_2:
                i += 1
                continue

            if i + 6 > len(self.buf):
                break

            cls = self.buf[i + 2]
            msg = self.buf[i + 3]
            length = self.buf[i + 4] | (self.buf[i + 5] << 8)

            frame_len = 6 + length + 2

            if i + frame_len > len(self.buf):
                break

            payload = self.buf[i + 6 : i + 6 + length]

            ck_a = self.buf[i + frame_len - 2]
            ck_b = self.buf[i + frame_len - 1]

            calc_a, calc_b = self._ck(self.buf[i + 2 : i + 6 + length])

            if ck_a != calc_a or ck_b != calc_b:
                # bad frame → shift by 1 and resync
                i += 1
                continue

            # valid packet → parse
            if cls == NAV_PVT_CLASS and msg == NAV_PVT_ID:
                self._parse_nav_pvt(payload)

            i += frame_len

        # drop processed bytes only (safe cut)
        self.buf = self.buf[i:]

    # -----------------------------
    # NAV-PVT PARSER (STABLE)
    # -----------------------------
    def _parse_nav_pvt(self, p):
        if len(p) < 92:
            return

        def u4(o):
            return (
                p[o]
                | (p[o + 1] << 8)
                | (p[o + 2] << 16)
                | (p[o + 3] << 24)
            )

        def i4(o):
            v = u4(o)
            return v - 0x100000000 if v & 0x80000000 else v

        fix_type = p[20]
        if fix_type < 2:
            return

        self.last_fix = {
            "lat": i4(28) / 1e7,
            "lon": i4(24) / 1e7,
        
            # altitude
            "alt": i4(32) / 1000,
        
            # accuracy estimates
            "h_acc": u4(36) / 1000,   # meters
            "v_acc": u4(40) / 1000,   # meters
        
            # motion
            "speed": u4(60) / 1000,   # m/s
        
            # heading (course over ground)
            "heading": i4(64) / 1e5,  # degrees
        
            # quality
            "sats": p[23],
            "fix": fix_type
        }

    # -----------------------------
    # MAIN LOOP (1 Hz SAFE)
    # -----------------------------
    def gps_loop(self):
        last_print = time.ticks_ms()

        while True:
            self._fill()
            self._process()

            # 1 Hz throttle (don’t spam CPU)
            now = time.ticks_ms()
            if time.ticks_diff(now, last_print) > 1000:
                last_print = now

                if self.last_fix:
                    print(
                        "LAT:", self.last_fix["lat"],
                        "LON:", self.last_fix["lon"],
                        "ALT:", self.last_fix["alt"],
                        "SATS:", self.last_fix["sats"],
                        "FIX:", self.last_fix["fix"]
                    )
                else:
                    print("NO FIX YET")

            time.sleep_ms(20)

    def poll(self):
        self._fill()
        self._process()
        return self.last_fix