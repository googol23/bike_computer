import math

# ----------------------------------------
# Optional GPX support
# ----------------------------------------

try:
    import gpxpy
    GPXPY_AVAILABLE = True
except ImportError:
    GPXPY_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

class Route:

    def __init__(self, name: str = "NONAME"):
        self.points: list[tuple[float, float, float]] = []
        self.name = name

    # ----------------------------------------
    # Basic methods
    # ----------------------------------------

    def add_point(self, lat, lon, elv):
        self.points.append((lat, lon, elv))

    def clear(self):
        self.points = []

    def length(self):
        return len(self.points)

    def last_point(self):
        if not self.points:
            return None
        return self.points[-1]

    # ----------------------------------------
    # Geometry
    # ----------------------------------------

    def perpendicular_distance(self, point, start, end):
        # 3D point-to-line distance using vector math
    
        def to_vec(a, b):
            return (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    
        if start == end:
            return math.sqrt(
                (point[0] - start[0])**2 +
                (point[1] - start[1])**2 +
                (point[2] - start[2])**2
            )
    
        sx, sy, sz = start
        ex, ey, ez = end
        px, py, pz = point
    
        ab = (ex - sx, ey - sy, ez - sz)
        ap = (px - sx, py - sy, pz - sz)
    
        ab_len2 = ab[0]**2 + ab[1]**2 + ab[2]**2
        if ab_len2 == 0:
            return math.sqrt(ap[0]**2 + ap[1]**2 + ap[2]**2)
    
        # cross product magnitude |AP x AB|
        cx = ap[1]*ab[2] - ap[2]*ab[1]
        cy = ap[2]*ab[0] - ap[0]*ab[2]
        cz = ap[0]*ab[1] - ap[1]*ab[0]
    
        cross_len = math.sqrt(cx*cx + cy*cy + cz*cz)
    
        return cross_len / math.sqrt(ab_len2)

    # ----------------------------------------
    # Simplification
    # ----------------------------------------
    def rdp(self, points=None, epsilon=0.0001):

        if points is None:
            points = self.points

        if len(points) < 3:
            return points

        dmax = 0
        index = 0

        start = points[0]
        end = points[-1]

        for i in range(1, len(points) - 1):

            d = self.perpendicular_distance(
                points[i],
                start,
                end
            )

            if d > dmax:
                index = i
                dmax = d

        if dmax > epsilon:

            left = self.rdp(points[:index + 1], epsilon)
            right = self.rdp(points[index:], epsilon)

            return left[:-1] + right

        return [start, end]

    # ----------------------------------------
    # Screen projection
    # ----------------------------------------
    def project_to_screen(self, width, height, padding=10):

        if not self.points:
            return []

        lats = [p[0] for p in self.points]
        lons = [p[1] for p in self.points]

        min_lat = min(lats)
        max_lat = max(lats)

        min_lon = min(lons)
        max_lon = max(lons)

        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon

        # avoid divide-by-zero
        if lat_range == 0:
            lat_range = 1

        if lon_range == 0:
            lon_range = 1

        scale_x = (width - 2 * padding) / lon_range
        scale_y = (height - 2 * padding) / lat_range

        scale = min(scale_x, scale_y)

        screen_points = []

        for lat, lon, _ in self.points:

            x = (lon - min_lon) * scale + padding

            y = height - (
                (lat - min_lat) * scale + padding
            )

            screen_points.append(
                (int(x), int(y))
            )

        return screen_points

    # ----------------------------------------
    # GPX support
    # ----------------------------------------

    @staticmethod
    def gpx_supported():
        return GPXPY_AVAILABLE

    def load_gpx_track(self, file_path):

        if not GPXPY_AVAILABLE:
            raise RuntimeError(
                "gpxpy package not available"
            )

        with open(file_path, 'r', encoding='utf-8') as f:
            gpx = gpxpy.parse(f)

        print("Tracks:", len(gpx.tracks))
        print("Routes:", len(gpx.routes))
        print("Waypoints:", len(gpx.waypoints))

        self.points = []

        # Tracks
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    self.add_point(
                        point.latitude,
                        point.longitude,
                        point.elevation,
                    )

        # Routes
        if not self.points:
            for route in gpx.routes:
                for point in route.points:
                    self.add_point(
                        point.latitude,
                        point.longitude,
                        point.elevation,
                    )

        return self.points

    def plot(self, simplified=None):
    
        if not MATPLOTLIB_AVAILABLE:
            print("matplotlib not available → plotting disabled")
            return
    
        import matplotlib.pyplot as plt
    
        if not self.points:
            print("No data to plot")
            return
    
        orig_lats = [p[0] for p in self.points]
        orig_lons = [p[1] for p in self.points]
    
        plt.figure()
    
        plt.plot(orig_lons, orig_lats, linewidth=1, label="Original")
    
        if simplified:
            simp_lats = [p[0] for p in simplified]
            simp_lons = [p[1] for p in simplified]
    
            plt.scatter(simp_lons, simp_lats, label="Simplified")
    
        plt.legend()
        plt.axis("equal")
        plt.title("Route comparison")
        plt.savefig("route_comparison.png")

    def plot_lcd(self, simplified=None, width=480, height=320, padding=10):
    
        if not MATPLOTLIB_AVAILABLE:
            print("matplotlib not available → LCD preview disabled")
            return
    
        import matplotlib.pyplot as plt
    
        def project(points):
    
            if not points:
                return []
    
            lats = [p[0] for p in points]
            lons = [p[1] for p in points]
    
            min_lat, max_lat = min(lats), max(lats)
            min_lon, max_lon = min(lons), max(lons)
    
            lat_range = max_lat - min_lat or 1
            lon_range = max_lon - min_lon or 1
    
            scale_x = (width - 2 * padding) / lon_range
            scale_y = (height - 2 * padding) / lat_range
            scale = min(scale_x, scale_y)
    
            screen = []
    
            for lat, lon, _ in points:
                x = (lon - min_lon) * scale + padding
                y = height - ((lat - min_lat) * scale + padding)
                screen.append((x, y))
    
            return screen
    
        orig = project(self.points)
        simp = project(simplified) if simplified else None
    
        plt.figure()
    
        # draw original
        if orig:
            ox, oy = zip(*orig)
            plt.plot(ox, oy, linewidth=1, label="Original")
    
        # draw simplified
        if simp:
            sx, sy = zip(*simp)
            plt.plot(sx, sy, linewidth=2, label="Simplified")
    
        plt.gca().invert_yaxis()  # match screen coordinates (0,0 top-left)
    
        plt.xlim(0, width)
        plt.ylim(0, height)
    
        plt.title("ESP32 LCD Preview")
        plt.legend()
        plt.savefig("lcd_preview.png")

    def export_as_py(self, filename: str | None, width: int, height: int) -> None:
        if not filename:
            filename = f"routes/{self.name}.py"
        
        with open(filename, "w") as f:
            f.write("points = [\n")
            
            for lat_pxl, lon_pxl, elv in self.points:
                f.write(f"    ({lat_pxl}, {lon_pxl}, {elv}),\n")
            f.write("]\n")

# ----------------------------------------
# Example
# ----------------------------------------

if __name__ == "__main__":

    route = Route()

    print("GPX support:",
          Route.gpx_supported())

    if Route.gpx_supported():

        route.load_gpx_track("route.gpx")

        print("Original:",
              route.length())

        simplified = route.rdp(
            epsilon=0.00005
        )

        print("Simplified:",
              len(simplified))

        screen = route.project_to_screen(
            480,
            320
        )

        print(screen[:5])

        route.plot(simplified)
        route.plot_lcd(simplified)

        route.export_as_py("routes/gpx_route.py", 320,240)