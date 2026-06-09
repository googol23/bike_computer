import math
import struct
import os

import hashlib
def compute_file_hash(path):
    """
    Return SHA-256 hex digest for the given file.

    MicroPython-compatible: tries `hashlib` then `uhashlib`, handles implementations
    that require initial data at construction, and uses a small chunk size to stay
    memory-friendly on constrained devices. Returns an empty string if hashing isn't
    available or fails.
    """
    # Import a hashing implementation that's available on the platform
    try:
        import hashlib as _hashlib
    except Exception:
        try:
            import uhashlib as _hashlib
        except Exception as e:
            print(e)
            return ""

    # Create the sha256 object; some MicroPython variants require initial bytes
    try:
        h = _hashlib.sha256()
    except TypeError:
        try:
            h = _hashlib.sha256(b"")
        except Exception:
            return ""

    # Read file in small binary chunks and update the digest
    try:
        f = open(path, "rb")
    except Exception:
        return ""

    try:
        while True:
            chunk = f.read(1024)
            if not chunk:
                break
            try:
                h.update(chunk)
            except Exception:
                # Some very limited implementations may not support update().
                # Try to recreate the digest with the chunk as initial data (best-effort).
                try:
                    h = _hashlib.sha256(chunk)
                except Exception:
                    f.close()
                    return ""
    finally:
        try:
            f.close()
        except Exception:
            pass

    # Return hex string: prefer hexdigest(), otherwise hex-encode digest()
    try:
        return h.hexdigest()
    except Exception:
        try:
            digest_bytes = h.digest()
            return "".join("{:02x}".format(b) for b in digest_bytes)
        except Exception:
            return ""

EARTH_RADIUS = 6371000  # meters


def distance_2d_m(lat1, lon1, lat2, lon2) -> float:
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

# ----------------------------
# Route simplification
# ----------------------------
def project(lat, lon, bounds, width=480, height=320):
    min_lat, max_lat, min_lon, max_lon = bounds

    x = (lon - min_lon) / (max_lon - min_lon) * width
    y = (max_lat - lat) / (max_lat - min_lat) * height

    return x, y

def perpendicular_distance(px, py, x1, y1, x2, y2):
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

def rdp(pts, epsilon=0.0001) -> list:

    n = len(pts)

    if n < 3:
        return []

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

