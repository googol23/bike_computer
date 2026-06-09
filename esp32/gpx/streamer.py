import os
import struct

from .navigation import NavigationStreamer
from .os_extensions import file_exists
from .route_cache import RouteCache, RouteCacheBinary
from .utils import compute_file_hash


class GPXStreamer:
    """
    GPXStreamer

    A small convenience wrapper around the on-disk route binary cache
    (RouteCacheBinary) that provides an easy streaming-style interface to
    read route points near a given position and to fetch individual points
    by index.

    Behavior
    - When instantiated with a GPX path, GPXStreamer derives a route name
      from the filename and checks for a prebuilt binary cache at
      `cache/routes/{route_name}.bin`.
    - If the binary cache does not exist or hash does not match, it calls
      `RouteCache().build_binary_cache(gpx_path)` to produce the binary file.
    - It then loads the binary cache with `RouteCacheBinary().load_route(...)`
      and delegates point/index lookups to that object.

    Notes
    - The binary format stores lat/lon as integers scaled by 1e7. `get_point`
      returns lat/lon as floats in degrees and elevation as an integer (meters).
    - GPXStreamer is a thin wrapper and relies on the underlying cache objects
      for heavy lifting (cache building, binary I/O, searching).
    - Not thread-safe: simultaneous access from multiple threads/processes is
      not supported.
    - File I/O errors (missing GPX file, permission issues) will surface from the
      underlying functions.

    Public methods
    - check_route_cache() -> bool
      Check whether the binary cache `cache/routes/{route_name}.bin` exists and has the correct hash.

    - get_point(i: int) -> tuple[float, float, int]
      Return the point at index `i` as `(lat_deg, lon_deg, elevation_m)`.

    - find_closest_point(lat: float, lon: float) -> tuple[int, tuple]
      Return `(index, point)` where `point` is the same tuple returned by
      `get_point`.

    - get_next_d_km(lat: float, lon: float, d: float) -> tuple[list, int]
      Return `(points_list, end_index)` containing the route points covering
      approximately `d` kilometers starting from the route location closest to
      `(lat, lon)`. `points_list` is a list of tuples `(lat_deg, lon_deg, elev)`.

    Example
        streamer = GPXStreamer("routes/my_route.gpx")
        if not streamer.check_route_cache():
            # cache will be created automatically on initialization
            pass
        lat, lon, ele = streamer.get_point(0)
        idx, (plat, plon, pele) = streamer.find_closest_point(49.87, 8.64)
        pts, end_idx = streamer.get_next_d_km(49.87, 8.64, 2.0)

    Possible follow-ups
    - Add type annotations on other methods for clarity and static checking.
    - Add a small unit test exercising cache creation + get_next_d_km.
    """

    def __init__(self, gpx_path):
        self.gpx_path = gpx_path
        self.route_name = gpx_path.split("/")[-1].replace(".gpx", "")
        self.bin_path = "cache/routes/" + self.route_name + ".bin"

        # If cache missing or hash mismatch, (re)build it
        if not self.check_route_cache():
            RouteCache().build_binary_cache(gpx_path)

        self.rcb = RouteCacheBinary()
        self.rcb.load_route(self.bin_path)

        self.gpx_pts:list[tuple[float,float,float]] = []

    def stream_navigation(self) -> NavigationStreamer:
        """
        Return a NavigationStreamer for this route. The streamer will load nav
        instructions from the route's .nav cache or from GPX if needed.
        """
        # ensure we stored gpx_path and route_name on init
        return NavigationStreamer(
            getattr(self, "gpx_path", None) or (self.route_name + ".gpx")
        )

    def check_route_cache(self) -> bool:
        """Check whether a matching binary cache exists for the current GPX.

        Returns True only if both the binary exists and the saved hash
        matches the current GPX file hash. If the meta file is missing or the
        hashes differ, returns False so the cache will be rebuilt.
        """
        bin_path = self.bin_path
        if not file_exists(bin_path):
            return False

        meta_path = bin_path.replace(".bin", ".sha256")
        if not file_exists(meta_path):
            # No metadata -> can't verify; force rebuild
            return False

        try:
            with open(meta_path, "r", encoding="utf-8") as mf:
                saved_hash = mf.read().strip()
            current_hash = compute_file_hash(self.gpx_path)
            if saved_hash == current_hash:
                return True
            else:
                print(
                    f"[INFO] GPX changed (hash mismatch). Rebuilding cache for {self.route_name}"
                )
                return False
        except Exception as e:
            print(f"[WARN] Failed to verify route cache hash: {e}")
            return False

    def get_point(self, i: int) -> tuple[float, float, float]:
        """Get the point at the given index"""
        p = self.rcb.get_point(i)
        return p[0] / 1e7, p[1] / 1e7, p[2]

    def find_closest_point(self, lat: float, lon: float) -> tuple[int, tuple]:
        """Find the closest point to the given lat/lon"""
        i = self.rcb.find_closest_index(lat, lon)
        return i, self.get_point(i)

    def get_next_d_km(self, lat: float | None, lon: float | None, d: float) -> list:
        """Get the next d km of the route"""
        if lat is None or lon is None:
            lat, lon, _ = self.rcb.get_point(0)
            lat /= 1e7
            lon /= 1e7
        self.gpx_pts = self.rcb.get_next_d_km(lat, lon, d)[0]
        return self.gpx_pts


def test_navigation_streamer(gpx_path="routes/arheilgen_to_Barcelona.gpx", step=2):
    """
    Simple test that:
    - constructs a GPXStreamer for `gpx_path`
    - creates a NavigationStreamer (via GPXStreamer.stream_navigation() when available)
    - walks through the route points from the binary cache (every `step` points)
    - calls nav.update_position(lat, lon) and prints the current instruction

    Adjust `step` to simulate GNSS frequency (larger -> fewer updates).
    """
    print(f"[TEST] gpx_path = {gpx_path}, step = {step}")

    # create GPXStreamer
    streamer = GPXStreamer(gpx_path)

    # get NavigationStreamer; try GPXStreamer.stream_navigation() if present,
    # otherwise instantiate directly
    try:
        nav = streamer.stream_navigation()
    except Exception:
        # fallback: construct NavigationStreamer directly
        nav = NavigationStreamer(gpx_path, getattr(streamer, "route_name", None))

    # Ensure nav instructions are loaded
    num_nav = nav.load()
    print(f"[TEST] Loaded {num_nav} navigation instructions")
    nav.print_nav_summary()

    # If binary route has count use it, else try to approximate by reading until EOF
    total_pts = getattr(streamer.rcb, "n", None)
    if total_pts is None:
        print("[TEST] route binary length unavailable; aborting")
        return

    print(f"[TEST] Streaming through {total_pts} route points (every {step})")

    for i in range(0, total_pts, step):
        lat, lon, ele = streamer.get_point(i)
        # feed GNSS update
        nav.update_position(lat, lon)

        cur = nav.get_current()
        print(f"[GNSS] idx={i} pos=({lat:.6f}, {lon:.6f}) ele={ele}")
        if cur:
            desc = cur.get("desc", "") or ""
            dist = cur.get("distance", 0.0)
            sign = cur.get("sign", 0)
            print(f"  [NAV] instr_idx={nav.idx} desc='{desc}' dist={dist} sign={sign}")
        else:
            print("  [NAV] no current instruction (end)")

    print("[TEST] done")


if __name__ == "__main__":
    test_navigation_streamer()
