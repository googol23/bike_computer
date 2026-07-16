import requests
import polyline
import math
from shapely.geometry import LineString, Polygon, shape
from shapely.ops import transform
import pyproj
import matplotlib.pyplot as plt

# =========================
# CONFIG
# =========================

ORS_API_KEY = "YOUR_API_KEY"

start = (50.1109, 8.6821)   # lat, lon
end   = (50.1200, 8.7000)

BUFFER_METERS = 20

# OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"


# =========================
# 1. ROUTE FROM ORS
# =========================
def get_route(start, end):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"

    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }

    body = {
        "coordinates": [
            [start[1], start[0]],
            [end[1], end[0]]
        ]
    }

    r = requests.post(url, json=body, headers=headers)
    data = r.json()

    if "routes" not in data:
        raise RuntimeError(data)

    encoded = data["routes"][0]["geometry"]
    coords = polyline.decode(encoded)

    # convert to (lon, lat)
    return [(lon, lat) for lat, lon in coords]


# =========================
# 2. SAFE 200m BUFFER (NO OSMNX)
# =========================
def build_corridor(route):
    line = LineString(route)

    # project to meters
    proj = pyproj.Transformer.from_crs(
        "EPSG:4326",
        "EPSG:3857",
        always_xy=True
    ).transform

    line_m = transform(proj, line)

    buffer_m = line_m.buffer(BUFFER_METERS)

    # back to lat/lon
    back = pyproj.Transformer.from_crs(
        "EPSG:3857",
        "EPSG:4326",
        always_xy=True
    ).transform

    return transform(back, buffer_m)


# =========================
# 3. OVERPASS QUERY (roads + terrain)
# =========================
def fetch_osm(corridor):
    minx, miny, maxx, maxy = corridor.bounds

    query = f"""
    [out:json][timeout:25];
    (
      way["highway"]({miny},{minx},{maxy},{maxx});
      way["natural"]({miny},{minx},{maxy},{maxx});
    );
    out geom;
    """

    r = requests.post(
        OVERPASS_URL,
        data=query.encode("utf-8")
    )

    print("STATUS:", r.status_code)
    print("HEAD:", r.text[:200])

    if r.status_code != 200:
        raise RuntimeError(f"Overpass failed: {r.status_code}")

    return r.json()


# =========================
# 4. FILTER TO CORRIDOR
# =========================
def extract_features(data, corridor):
    features = []

    for el in data.get("elements", []):
        if "geometry" not in el:
            continue

        coords = [(p["lon"], p["lat"]) for p in el["geometry"]]

        geom = LineString(coords)

        if corridor.intersects(geom):
            tag = el.get("tags", {})
            name = tag.get("highway") or tag.get("natural") or "feature"
            features.append((name, coords))

    return features


# =========================
# 5. SIMPLIFY TO RELATIVE COORDS
# =========================
def to_relative(features, origin):
    ox, oy = origin
    out = []

    for name, coords in features:
        out.append(name)

        for lon, lat in coords:
            dx = (lon - ox) * 111320
            dy = (lat - oy) * 110540
            out.append(f"{dx:.1f},{dy:.1f}")

        out.append("END")

    return out


# =========================
# 6. SAVE FILE
# =========================
def save(lines, filename="output.txt"):
    with open(filename, "w") as f:
        f.write("\n".join(lines))


# =========================
# 7. PLOT FOR DEBUG
# =========================
def plot(route, features):
    plt.figure()

    # route
    xs = [p[0] for p in route]
    ys = [p[1] for p in route]
    plt.plot(xs, ys, label="route")

    # features
    for _, coords in features:
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        plt.plot(xs, ys, alpha=0.5)

    plt.axis("equal")
    plt.legend()
    plt.savefig("debug.png")


# =========================
# MAIN
# =========================
print("Fetching route...")
route = get_route(start, end)

print("Building corridor...")
corridor = build_corridor(route)

print("Fetching OSM...")
raw = fetch_osm(corridor)

print("Extracting features...")
features = extract_features(raw, corridor)

print("Converting to relative...")
print("Features:", len(features))


origin = route[0]

out = to_relative(features, origin)
print("Saving...")
save(out)

plot(route, features)

print("DONE -> output.txt")