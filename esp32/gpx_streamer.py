import math

EARTH_RADIUS = 6371000  # meters


def distance_2d_m(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0
    
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat * 0.5) ** 2 +
        math.cos(lat1) * math.cos(lat2) *
        math.sin(dlon * 0.5) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS * c

def distance_3d_m(lat1, lon1, ele1, lat2, lon2, ele2):
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    

    ground = 2 * EARTH_RADIUS * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    delev = (ele2 - ele1)

    dist = math.sqrt(ground * ground + delev * delev)

    return dist

    
class GPXStreamReader:
    """
    Lightweight streaming GPX reader for ESP32.

    - Returns N points at a time
    - Keeps internal file cursor
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        print(f"Opening GPX file: {file_path}")
        self.file = open(file_path, "r", encoding="utf-8")

        self._in_trkpt = False

        self._lat = 0.0
        self._lon = 0.0
        self._ele = 0.0

        self.nav_pts = []

        self.gpx_pts = []

        self._eof = False

    # ----------------------------
    # internal parsing helpers
    # ----------------------------
    def load_navigation(self):
        print("[NAV] Loading navigation (ESP32 mode)...")
    
        self.file.seek(0)
        self._eof = False
        self.nav_pts = []
    
        current: dict = {}
        in_rtept = False
    
        for raw in self.file:
            
            line = raw.strip()
    
            # start route point
            if "<rtept" in line:
                lat = self._parse_float_attr(line, "lat")
                lon = self._parse_float_attr(line, "lon")

   
                current = {
                    "lat": lat,
                    "lon": lon,
                    "desc": "",
                    "distance": 0.0,
                    "sign": 0
                }
    
                in_rtept = True
    
            if not in_rtept:
                continue
    
            # description (direct child)
            if "<desc>" in line:
                a = line.find("<desc>") + 6
                b = line.find("</desc>")
                if a != -1 and b != -1:
                    current["desc"] = line[a:b].strip()

            # gh:distance (inside extensions)
            if "gh:distance" in line:
                a = line.find("<gh:distance>") + len("<gh:distance>")
                b = line.find("</gh:distance>")
                if a != -1 and b != -1:
                    try:
                        current["distance"] = float(line[a:b])
                    except:
                        current["distance"] = 0.0

            if "gh:sign" in line:
                a = line.find("<gh:sign>") + len("<gh:sign>")
                b = line.find("</gh:sign>")
                if a != -1 and b != -1:
                    try:
                        current["sign"] = int(line[a:b])
                    except:
                        current["sign"] = None
                        
            # close route point
            if "</rtept>" in line and len(current):
                self.nav_pts.append(current)
                current = {}
                in_rtept = False

    
        self.file.seek(0)
        print(f"[NAV] DONE. {len(self.nav_pts)} instructions loaded")
        
    def _parse_float_attr(self, line, key):
        idx = line.find(key + '="')
        if idx == -1:
            return None
        start = idx + len(key) + 2
        end = line.find('"', start)
        return float(line[start:end])

    def _parse_ele(self, line):
        try:
            return float(line.replace("<ele>", "").replace("</ele>", ""))
        except:
            return 0.0

    # ----------------------------
    # Route simplification
    # ----------------------------
    def project(self,lat, lon, bounds, width=480, height=320):
        min_lat, max_lat, min_lon, max_lon = bounds
    
        x = (lon - min_lon) / (max_lon - min_lon) * width
        y = (max_lat - lat) / (max_lat - min_lat) * height
    
        return x, y

    def perpendicular_distance(self,px, py, x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1
    
        if dx == 0 and dy == 0:
            return ((px - x1)**2 + (py - y1)**2) ** 0.5
    
        t = ((px - x1) * dx + (py - y1) * dy) / (dx*dx + dy*dy)
    
        if t < 0:
            x, y = x1, y1
        elif t > 1:
            x, y = x2, y2
        else:
            x, y = x1 + t * dx, y1 + t * dy
    
        return ((px - x)**2 + (py - y)**2) ** 0.5

    def rdp(self, epsilon=0.0001) -> list:
        pts = self.gpx_pts
        n = len(pts)
    
        if n < 3:
            return []
    
        perpendicular_distance = self.perpendicular_distance
    
        stack = [(0, n - 1)]
        keep = [False] * n
        keep[0] = True
        keep[n - 1] = True
    
        while stack:
            start, end = stack.pop()
    
            x1, y1, _ = pts[start]
            x2, y2, _ = pts[end]
    
            dx = x2 - x1
            dy = y2 - y1
    
            max_dist = -1.0
            index = start
    
            for i in range(start + 1, end):
                x, y, _ = pts[i]
    
                d = perpendicular_distance(x, y, x1, y1, x2, y2)
    
                if d > max_dist:
                    max_dist = d
                    index = i
    
            if max_dist > epsilon:
                keep[index] = True
                stack.append((start, index))
                stack.append((index, end))
    
        return [pts[i] for i in range(n) if keep[i]]
    
    
    # ----------------------------
    # main streaming method
    # ----------------------------
    def next_points(self, n: int):
        """
        Collect the next N GPX points as [(lat, lon, ele), ...]
        """

        if self._eof:
            return

        self.gpx_pts.clear()

        for line in self.file:

            line = line.strip()

            # detect start of track point
            if "<trkpt" in line:
                self._in_trkpt = True

                lat = self._parse_float_attr(line, "lat")
                lon = self._parse_float_attr(line, "lon")

                if lat is not None:
                    self._lat = lat
                if lon is not None:
                    self._lon = lon

                self._ele = 0.0
                continue

            if self._in_trkpt:

                if "<ele>" in line:
                    self._ele = self._parse_ele(line)

                if "</trkpt>" in line:
                    self.gpx_pts.append((self._lat, self._lon, self._ele))
                    self._in_trkpt = False

                    if len(self.gpx_pts) >= n:
                        return

        # reached EOF
        self._eof = True


    def next_km(self, target_km: float):
        if self._eof:
            return
    
        self.gpx_pts.clear()
    
        prev = None
        distance = 0.0
    
        in_trkpt = False
        lat = lon = ele = 0.0
    
        for line in self.file:
            line = line.strip()
    
            # fast reject
            if "<trkpt" in line:
                in_trkpt = True
    
                lat = self._parse_float_attr(line, "lat")
                lon = self._parse_float_attr(line, "lon")
    
                ele = 0.0
    
                # ele may be on same line
                e1 = line.find("<ele>")
                if e1 != -1:
                    e2 = line.find("</ele>", e1)
                    if e2 != -1:
                        ele = float(line[e1 + 5:e2])
    
            if not in_trkpt:
                continue
    
            # ele split across lines (rare but safe)
            if line.startswith("<ele>") and ele == 0.0:
                ele = self._parse_ele(line)
    
            if "</trkpt>" in line:
                current = (lat, lon, ele)
    
                self.gpx_pts.append(current)
    
                if prev is not None:
                    distance += distance_3d_m(
                        prev[0], prev[1], prev[2],
                        current[0], current[1], current[2]
                    ) * 0.001
    
                prev = current
                in_trkpt = False
    
                if distance >= target_km:
                    return

        self._eof = True

        
    # ----------------------------
    # reset / reuse
    # ----------------------------

    def reset(self):
        """Restart reading from beginning"""
        self.file.seek(0)
        self._in_trkpt = False
        self._eof = False

    def close(self):
        if not self.file.closed:
            self.file.close()



if __name__ == "__main__":
    streamer = GPXStreamReader("routes/arheilgen_to_ludwigsturm.gpx")

    # 
    # while True:
    #     points = streamer.next_points(5)

    #     print(points, "\n")
        
    #     if not points:
    #         break
        
    streamer.load_navigation()
    for pt in streamer.nav_pts:
        print(pt)
        