
import sys
import os
import struct
from .route_cache import RouteCacheBinary, RouteCache, NAV_HEADER_SIZE, NAV_HEADER_FMT, NAV_RECORD_HDR_SIZE, NAV_RECORD_FMT, route_cache_signature
from .utils import distance_2d_m
from .os_extensions import file_exists
class NavigationStreamer:
    """
    Stream navigation instructions for a route.

    Responsibilities:
    - Load nav instructions from a compact .nav cache file (fast), or parse the GPX
      <rtept> section as a fallback.
    - Maintain an internal current-index and provide simple GNSS-driven advancement.
    - Expose separate methods for nav-file reading and GPX parsing so you can test
      or select either approach independently.

    Record binary format (per-record):
      struct "<iifhH"
        i  int32  lat_i   (latitude * 1e7)
        i  int32  lon_i   (longitude * 1e7)
        f  float  distance_m
        h  int16  sign
        H  uint16 desc_len
      followed by desc_len bytes of UTF-8 description text.
    """

    def __init__(self, gpx_path: str, route_name: str | None = None, auto_build: bool = True):
        self.gpx_path = gpx_path
        self.route_name = route_name or gpx_path.split("/")[-1].replace(".gpx", "")
        self.nav_path = f"cache/routes/{self.route_name}.nav"
        self.meta_path = f"cache/routes/{self.route_name}.sha256"

        # in-memory list of nav entries: dicts with keys lat, lon, distance, sign, desc
        self.nav_pts: list[dict] = []
        self.idx = 0  # current instruction index

        self._initialized = False

        # Optionally build cache if missing/invalid
        if auto_build and not self._nav_cache_valid():
            try:
                print(f"NavigationStreamer: building cache for {self.gpx_path}")
                RouteCache().build_binary_cache(self.gpx_path)
            except Exception as e:
                print(f"[WARN] NavigationStreamer: failed to build cache: {e}")

        self.load()
        print(f"NavigationStreamer: loaded {len(self.nav_pts)} nav points from {self.gpx_path}")

    # ---- cache validation & loading orchestration ----
    def _nav_cache_valid(self) -> bool:
        """Return True if the .nav file exists and the meta hash matches the GPX."""
        if not file_exists(self.nav_path):
            return False
        if not file_exists(self.meta_path):
            return False
        try:
            with open(self.meta_path, "r", encoding="utf-8") as mf:
                saved_hash = mf.read().strip()
            cur_hash = route_cache_signature(self.gpx_path)
            return saved_hash == cur_hash
        except Exception:
            return False

    def load(self, prefer_cache: bool = True) -> int:
        """
        Load navigation instructions into memory.

        prefer_cache: if True, try reading from .nav first (if valid), otherwise parse GPX.
        Returns the number of navigation entries loaded.
        """
        self.nav_pts.clear()
        self.idx = 0

        if prefer_cache and self._nav_cache_valid() and file_exists(self.nav_path):
            ok = self.read_from_nav_file()
            if ok:
                return len(self.nav_pts)

        # fallback to parsing GPX rtept entries
        count = self.parse_gpx_navigation()
        return count

    # ---- nav file reader (separated) ----
    def read_from_nav_file(self) -> bool:
        """
        Read nav instructions from the binary .nav file into self.nav_pts.
        Returns True on success, False on error.
        """
        if not file_exists(self.nav_path):
            return False

        try:
            with open(self.nav_path, "rb") as f:
                hdr = f.read(NAV_HEADER_SIZE)
                if len(hdr) < NAV_HEADER_SIZE:
                    return False
                count = struct.unpack(NAV_HEADER_FMT, hdr)[0] if hasattr(self, "NAV_HEADER_FMT") else struct.unpack("<I", hdr)[0]
                # iterate records
                for _ in range(count):
                    hdata = f.read(NAV_RECORD_HDR_SIZE)
                    if len(hdata) != NAV_RECORD_HDR_SIZE:
                        # truncated/corrupt file
                        return False
                    lat_i, lon_i, distance_f, sign_i, desc_len = struct.unpack(NAV_RECORD_FMT, hdata)
                    desc_bytes = f.read(desc_len) if desc_len else b""
                    desc = desc_bytes.decode("utf-8") if desc_bytes else ""
                    self.nav_pts.append({
                        "lat": lat_i / 1e7,
                        "lon": lon_i / 1e7,
                        "distance": float(distance_f),
                        "sign": int(sign_i),
                        "desc": desc
                    })
            return True
        except Exception as e:
            print(f"[WARN] NavigationStreamer.read_from_nav_file failed: {sys.print_exception(e)}")
            # Ensure partial state is cleared
            self.nav_pts.clear()
            return False

    # ---- GPX parsing (separated) ----
    def parse_gpx_navigation(self) -> int:
        """
        Parse <rtept> entries from the GPX file and load them into self.nav_pts.
        Robust to entries split across lines. Returns the number of entries parsed.
        """
        try:
            with open(self.gpx_path, "r", encoding="utf-8") as fin:
                in_rtept = False
                current = {}
                for raw in fin:
                    line = raw.strip()

                    # start of rtept (may contain attrs and inline children)
                    if "<rtept" in line:
                        lat = None
                        lon = None
                        try:
                            # parse attributes lat="..." lon="..."
                            idx = line.find('lat="')
                            if idx != -1:
                                s = idx + 5
                                e = line.find('"', s)
                                lat = float(line[s:e])
                            idx2 = line.find('lon="')
                            if idx2 != -1:
                                s = idx2 + 5
                                e = line.find('"', s)
                                lon = float(line[s:e])
                        except Exception:
                            lat = None
                            lon = None

                        current = {
                            "lat": lat,
                            "lon": lon,
                            "desc": "",
                            "distance": 0.0,
                            "sign": 0
                        }
                        in_rtept = True

                        # handle same-line children
                        if "<desc>" in line and "</desc>" in line:
                            a = line.find("<desc>") + 6
                            b = line.find("</desc>")
                            current["desc"] = line[a:b].strip()

                        if "<gh:distance>" in line and "</gh:distance>" in line:
                            try:
                                a = line.find("<gh:distance>") + len("<gh:distance>")
                                b = line.find("</gh:distance>")
                                current["distance"] = float(line[a:b])
                            except:
                                current["distance"] = 0.0

                        if "<gh:sign>" in line and "</gh:sign>" in line:
                            try:
                                a = line.find("<gh:sign>") + len("<gh:sign>")
                                b = line.find("</gh:sign>")
                                current["sign"] = int(line[a:b])
                            except:
                                current["sign"] = 0

                        # continue to next line (still inside rtept)
                        continue

                    if not in_rtept:
                        continue

                    # handle multi-line children
                    if "<desc>" in line and "</desc>" in line:
                        a = line.find("<desc>") + 6
                        b = line.find("</desc>")
                        current["desc"] = line[a:b].strip()

                    if "<gh:distance>" in line and "</gh:distance>" in line:
                        try:
                            a = line.find("<gh:distance>") + len("<gh:distance>")
                            b = line.find("</gh:distance>")
                            current["distance"] = float(line[a:b])
                        except:
                            current["distance"] = 0.0

                    if "<gh:sign>" in line and "</gh:sign>" in line:
                        try:
                            a = line.find("<gh:sign>") + len("<gh:sign>")
                            b = line.find("</gh:sign>")
                            current["sign"] = int(line[a:b])
                        except:
                            current["sign"] = 0

                    # end of rtept
                    if "</rtept>" in line and len(current):
                        if current.get("lat") is not None and current.get("lon") is not None:
                            self.nav_pts.append(current.copy())
                        current = {}
                        in_rtept = False

            return len(self.nav_pts)
        except Exception as e:
            print(f"[WARN] NavigationStreamer.parse_gpx_navigation failed: {e}")
            self.nav_pts.clear()
            return 0

    # ---- runtime API ----
    def get_current(self) -> dict | None:
        """Return the current instruction dict or None if none available / past end."""
        if not self.nav_pts:
            return None
        if self.idx < 0:
            self.idx = 0
        if self.idx >= len(self.nav_pts):
            return None
        return self.nav_pts[self.idx]

    def next(self) -> dict | None:
        """Advance to the next instruction and return it (None if at end)."""
        if not self.nav_pts:
            return None
        if self.idx < len(self.nav_pts) - 1:
            self.idx += 1
            return self.get_current()
        # go past end
        self.idx = len(self.nav_pts)
        return None

    def reset(self):
        """Reset internal index to beginning."""
        self.idx = 0

    def update_position(self, lat: float, lon: float, trigger_m: float = 15.0):
        """
        Provide GNSS updates. Behavior:
        - On first update, jump to the closest instruction (initialization).
        - Then use the improved decision order:
            * If a global closest instruction is meaningfully closer than current -> jump
            * If within trigger_m of current -> advance
            * If next instruction is significantly closer than current -> advance
        """
        if not self.nav_pts:
            return

        # print("NavigationStreamer got GNSS update: ", lat, lon)
        # print("Current instriction: ", self.get_current())

        # ensure idx in range
        if self.idx < 0:
            self.idx = 0
        if self.idx >= len(self.nav_pts):
            return

        # On first GNSS update, set current to the closest nav instruction
        if not self._initialized:
            closest = self.find_closest_index(lat, lon)
            print(f"First GNSS update, finding closes intruction on current route: {closest}")
            self._initialized = True
            if closest >= 0:
                self.idx = closest

            return  # don't advance further on the very first fix

        cur = self.get_current()
        if cur is None:
            return

        cur_d = distance_2d_m(lat, lon, cur["lat"], cur["lon"])

        # find absolute closest instruction (global)
        closest_idx = self.find_closest_index(lat, lon)
        closest_d = distance_2d_m(lat, lon, self.nav_pts[closest_idx]["lat"], self.nav_pts[closest_idx]["lon"])

        # If the absolute closest instruction is much closer than current, jump to it.
        HYSTERESIS = 5.0  # meters
        if closest_idx != self.idx and (closest_d + HYSTERESIS) < cur_d:
            self.idx = closest_idx
            return True

        # If we are within trigger distance of the current instruction, advance.
        if cur_d <= trigger_m:
            self.next()
            return True

        # Consider advancing to the next instruction if it is meaningfully closer than current.
        if self.idx + 1 < len(self.nav_pts):
            nxt = self.nav_pts[self.idx + 1]
            nxt_d = distance_2d_m(lat, lon, nxt["lat"], nxt["lon"])
            if (nxt_d + HYSTERESIS) < cur_d:
                self.next()
                return True

    def find_closest_index(self, lat: float, lon: float) -> int:
        """Return index of the instruction closest to (lat, lon), or -1 if none."""
        if not self.nav_pts:
            return -1
        best = 0
        best_d = distance_2d_m(lat, lon, self.nav_pts[0]["lat"], self.nav_pts[0]["lon"])
        for i in range(1, len(self.nav_pts)):
            d = distance_2d_m(lat, lon, self.nav_pts[i]["lat"], self.nav_pts[i]["lon"])
            if d < best_d:
                best_d = d
                best = i
        return best

    def jump_to_closest(self, lat: float, lon: float):
        """Set current index to the nav instruction closest to (lat, lon)."""
        idx = self.find_closest_index(lat, lon)
        if idx >= 0:
            self.idx = idx

    def print_nav_summary(self, limit: int = 10):
        """
        Print a short summary of the first `limit` nav entries (for debugging).
        Call this right after loading to verify the nav records.
        """
        n = len(self.nav_pts)
        print(f"[NAV] total entries = {n}")
        for i, e in enumerate(self.nav_pts[:limit]):
            lat = e.get("lat")
            lon = e.get("lon")
            desc = e.get("desc", "") or ""
            dist = e.get("distance", 0.0)
            sign = e.get("sign", 0)
            print(f"  [{i}] lat={lat:.6f} lon={lon:.6f} dist={dist} sign={sign} desc='{desc}'")


