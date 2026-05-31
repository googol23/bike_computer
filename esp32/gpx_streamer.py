import math

EARTH_RADIUS = 6371000  # meters

def distance_2d_km(lat1, lon1, lat2, lon2):
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


def distance_3d_km(lat1, lon1, ele1, lat2, lon2, ele2):
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)

    ground = 2 * EARTH_RADIUS * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    delev = (ele2 - ele1)

    dist = math.sqrt(ground * ground + delev * delev)

    return dist / 1000.0  # km
    
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

        self._eof = False

    # ----------------------------
    # internal parsing helpers
    # ----------------------------

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
    # main streaming method
    # ----------------------------
    def next_points(self, n: int):
        """
        Return next N GPX points as [(lat, lon, ele), ...]
        """

        if self._eof:
            return []

        points = []

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
                    points.append((self._lat, self._lon, self._ele))
                    self._in_trkpt = False

                    if len(points) >= n:
                        return points

        # reached EOF
        self._eof = True
        self.file.close()

        return points

    def next_km(self, target_km: float):
    
        if self._eof:
            return []
    
        points = []
    
        prev = None
        distance = 0.0
    
        for line in self.file:
    
            line = line.strip()
    
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
                    current = (self._lat, self._lon, self._ele)
    
                    points.append(current)
    
                    if prev is not None:
                        distance += distance_3d_km(
                            prev[0], prev[1], prev[2],
                            current[0], current[1], current[2]
                        )
    
                    prev = current
                    self._in_trkpt = False
    
                    if distance >= target_km:
                        return points
    
        self._eof = True
        self.file.close()
    
        return points
        
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
    streamer = GPXStreamReader("routes/arheilgen_to_Bessungen.gpx")
    while True:
        points = streamer.next_points(5)

        print(points, "\n")
        
        if not points:
            break
        