import struct
import os
from .utils import compute_file_hash, distance_2d_m



RTE_HEADER_FMT = "<IiiHiiHhh"
RTE_HEADER_SIZE = struct.calcsize(RTE_HEADER_FMT)
RTE_POINT_FMT  = "<iiH"   # lat, lon, elev
RTE_POINT_SIZE = struct.calcsize(RTE_POINT_FMT)

# struct for fixed-size part of each nav record
NAV_RECORD_FMT = "<iifhH"
MAX_DESC_LEN = 0xFFFF  # must fit uint16
NAV_HEADER_FMT = "<I"
NAV_RECORD_HDR_SIZE = struct.calcsize(NAV_RECORD_FMT)
NAV_HEADER_SIZE = struct.calcsize(NAV_HEADER_FMT)

CACHE_META = {
    "version": 1,
    "rte_header": RTE_HEADER_FMT,
    "rte_point": RTE_POINT_FMT,
    "nav_record": NAV_RECORD_FMT,
}
def cache_signature():
    return (
        str(CACHE_META["version"]) + "|" +
        CACHE_META["rte_header"] + "|" +
        CACHE_META["rte_point"] + "|" +
        CACHE_META["nav_record"]
    )

class RouteCache:

    def __init__(self):
        self.lats = []   # int32
        self.lons = []   # int32
        self.elvs = []   # int16 (or int32 if needed)
        self.seg  = []   # float OR int16 meters
        self.cum  = []   # float OR int32 meters
        

        self.bin_file = None
        self.n = 0
        
    def _parse_attr(self,line, key):
        k = key + '="'
        i = line.find(k)
        if i < 0:
            return None
        i += len(k)
        j = line.find('"', i)
        if j < 0:
            return None
        return float(line[i:j])
    
    def _parse_ele(self,line):
        a = "<ele>"
        b = "</ele>"
        i = line.find(a)
        j = line.find(b)
        if i < 0 or j < 0:
            return None
        return float(line[i+len(a):j])
       
    def load_route(self, gpx_file_path):
        self.gpx_file_path = gpx_file_path
        self.lats = []
        self.lons = []
        self.elvs = []
        self.seg = []
        self.cum = []
    
        total = 0.0
        prev_lat = None
        prev_lon = None
    
        f = open(gpx_file_path, "r")
    
        for line in f:
    
            if "<trkpt" not in line:
                continue
    
            lat = self._parse_attr(line, "lat")
            lon = self._parse_attr(line, "lon")
            ele = self._parse_ele(line)

            if lat is None or lon is None:
                continue
    
            lat_i = int(lat * 1e7)
            lon_i = int(lon * 1e7)
    
            self.lats.append(lat_i)
            self.lons.append(lon_i)
            self.elvs.append(int(ele) if ele is not None else 0)
    
            if prev_lat is None or prev_lon is None:
                self.seg.append(0)
                self.cum.append(0)
            else:
                d = distance_2d_m(
                    prev_lat / 1e7,
                    prev_lon / 1e7,
                    lat,
                    lon
                )
    
                d_i = int(d)
    
                self.seg.append(d_i)
                total += d_i
                self.cum.append(total)
    
            prev_lat = lat_i
            prev_lon = lon_i
    
        f.close()

    def find_closest_index(self, lat, lon):
    
        lat_f = lat * 1e7
        lon_f = lon * 1e7
    
        n = len(self.lats)
        best_i = 0
        best_d = 1e30
    
        step = max(1, n // 200)
    
        i = 0
        while i < n:
            d = distance_2d_m(
                lat,
                lon,
                self.lats[i] / 1e7,
                self.lons[i] / 1e7
            )
    
            if d < best_d:
                best_d = d
                best_i = i
    
            i += step
    
        # refine
        start = max(0, best_i - step)
        end = min(n - 1, best_i + step)
    
        i = start
        while i <= end:
            d = distance_2d_m(
                lat,
                lon,
                self.lats[i] / 1e7,
                self.lons[i] / 1e7
            )
    
            if d < best_d:
                best_d = d
                best_i = i
    
            i += 1
    
        return best_i

    def get_next_d_km(self, gnss_lat, gnss_lon, d_km):
    
        if not self.lats:
            return []
    
        start_i = self.find_closest_index(gnss_lat, gnss_lon)
    
        target = d_km * 1000
        acc = 0
    
        out = []
    
        i = start_i
    
        while i < len(self.lats):
    
            out.append((
                self.lats[i] / 1e7,
                self.lons[i] / 1e7,
                self.elvs[i]
            ))
    
            if i > start_i:
                acc += self.seg[i]
    
                if acc >= target:
                    break
    
            i += 1

        return out, start_i

    def build_binary_cache(self, gpx_path:str, out_path:str | None = None):
      
        """
        Build both the point binary (.bin) and a companion navigation cache (.nav).
        Writes a shared SHA-256 file cache/routes/{route_name}.sha256 containing the
        hash of the source GPX to detect changes later.
        """
        # prepare paths
        route_name = gpx_path.split("/")[-1].replace(".gpx", "")
        bin_out = f"cache/routes/{route_name}.bin"
        nav_out = f"cache/routes/{route_name}.nav"
        meta_out = f"cache/routes/{route_name}.sha256"

            
        # ensure output directory
        try:
            os.makedirs("cache/routes/", exist_ok=True)
        except Exception:
            pass

        # compute hash for GPX (so we can invalidate cache later)
        try:
            meta_hash = compute_file_hash(cache_signature())
            gp_hash = compute_file_hash(gpx_path + meta_hash)
        except Exception as e:
            print(f"[WARN] could not compute hash for {gpx_path}: {e}")
            gp_hash = ""
            
        # --- build .bin (trkpt) ---
        fin = open(gpx_path, "r", encoding="utf-8")
        fout = open(bin_out, "wb")

        # reserve header
        fout.write(b"\x00" * RTE_HEADER_SIZE)
        count = 0
        start_lat_i = 0
        start_lon_i = 0
        start_elv_i = 0
        
        end_lat_i = 0
        end_lon_i = 0
        end_elv_i = 0
        
        min_elv = 32767
        max_elv = -32768

        for line in fin:
            if "<trkpt" not in line:
                continue

            lat = self._parse_attr(line, "lat")
            lon = self._parse_attr(line, "lon")
            ele = self._parse_ele(line)

            if lat is None or lon is None:
                continue

            lat_i = int(lat * 1e7)
            lon_i = int(lon * 1e7)
            ele_i = int(ele) if ele is not None else 0

            if count == 0:
                start_lat_i = lat_i
                start_lon_i = lon_i
                start_elv_i = ele_i
            
            end_lat_i = lat_i
            end_lon_i = lon_i
            end_elv_i = ele_i
            
            min_elv = min(min_elv, ele_i)
            max_elv = max(max_elv, ele_i)

            fout.write(struct.pack(RTE_POINT_FMT, lat_i, lon_i, ele_i))
            count += 1

        fin.close()
        fout.seek(0)
        
        fout.write(
            struct.pack(
                RTE_HEADER_FMT,
                count,
                start_lat_i,
                start_lon_i,
                start_elv_i,
                end_lat_i,
                end_lon_i,
                end_elv_i,
                min_elv,
                max_elv,
            )
        )
        fout.close()

        # --- build .nav (rtept) ---
        # parse rtept entries robustly across lines (like GPXStreamReader.load_navigation)
        fin = open(gpx_path, "r", encoding="utf-8")

        # write nav binary with simple variable-length record format
        # header: uint32 count
        # record: int32 lat, int32 lon, float32 distance_m, int16 sign, uint16 desc_len, bytes(desc)
        nav_fout = open(nav_out, "wb")
        nav_fout.write(struct.pack("<I", 0))  # placeholder

        nav_count = 0

        for raw in fin:
            line = raw.strip()

            # accept single-line rtept entries (common) - keep the simple parser
            if "<rtept" in line and "</rtept>" in line:
                lat = self._parse_attr(line, "lat")
                lon = self._parse_attr(line, "lon")

                if lat is None or lon is None:
                    continue

                # defaults
                entry_distance = 0.0
                entry_sign = 0
                entry_desc = ""

                # description
                if "<desc>" in line and "</desc>" in line:
                    a = line.find("<desc>") + len("<desc>")
                    b = line.find("</desc>", a)
                    if a != -1 and b != -1:
                        entry_desc = line[a:b].strip()

                # gh:distance (use len, strip)
                if "<gh:distance>" in line and "</gh:distance>" in line:
                    a = line.find("<gh:distance>") + len("<gh:distance>")
                    b = line.find("</gh:distance>", a)
                    if a != -1 and b != -1:
                        try:
                            entry_distance = float(line[a:b].strip())
                        except:
                            entry_distance = 0.0

                # gh:sign
                if "<gh:sign>" in line and "</gh:sign>" in line:
                    a = line.find("<gh:sign>") + len("<gh:sign>")
                    b = line.find("</gh:sign>", a)
                    if a != -1 and b != -1:
                        try:
                            entry_sign = int(line[a:b].strip())
                        except:
                            entry_sign = 0

                # pack binary record
                lat_i = int(lat * 1e7)
                lon_i = int(lon * 1e7)
                dist_f = float(entry_distance)
                sign_i = int(entry_sign)
                desc_bytes = (entry_desc or "").encode("utf-8")

                # clamp description to uint16 length
                if len(desc_bytes) > MAX_DESC_LEN:
                    desc_bytes = desc_bytes[:MAX_DESC_LEN]

                desc_len = len(desc_bytes)

                # pack fixed-size header and write variable-length desc
                header = struct.pack(NAV_RECORD_FMT, lat_i, lon_i, dist_f, sign_i, desc_len)
                nav_fout.write(header)
                if desc_len:
                    nav_fout.write(desc_bytes)

                nav_count += 1

        fin.close()
        nav_fout.seek(0)
        nav_fout.write(struct.pack("<I", nav_count))
        nav_fout.close()
        
        # write companion hash file so we can detect GPX changes later
        try:
            with open(meta_out, "w", encoding="utf-8") as mf:
                mf.write(gp_hash)
        except Exception as e:
            print(f"[WARN] Failed to write meta hash file {meta_out}: {e}")




class RouteCacheBinary:
    def __init__(self):
        self.bin_file = None
        self.n = 0

    def __str__(self):
        return f"""RouteCacheBinary(
        n={self.n},
        start_lat={self.start_lat},
        start_lon={self.start_lon},
        end_lat={self.end_lat},
        end_lon={self.end_lon}
        min_elv={self.min_elv},
        max_elv={self.max_elv},
        )
        """

    def load_route(self, bin_path):
        self.bin_file = open(bin_path, "rb")
        header = self.bin_file.read(RTE_HEADER_SIZE)
        
        (
            self.n,
            self.start_lat,
            self.start_lon,
            self.start_elv,
            self.end_lat,
            self.end_lon,
            self.end_elv,
            self.min_elv,
            self.max_elv,
        ) = struct.unpack(RTE_HEADER_FMT, header)

        print(self.__str__())

    def get_point(self, i) -> tuple[int, int, int]:
        offset = RTE_HEADER_SIZE + i * RTE_POINT_SIZE
        self.bin_file.seek(offset)
        data = self.bin_file.read(RTE_POINT_SIZE)

        lat, lon, ele = struct.unpack(RTE_POINT_FMT, data)

        return lat, lon, ele

    def find_closest_index(self, lat, lon):
        best_i = 0
        best_d = 1e18
        step = max(1, self.n // 200)

        # coarse scan
        i = 0
        while i < self.n:
            p = self.get_point(i)

            d = distance_2d_m(
                lat, lon,
                p[0] / 1e7,
                p[1] / 1e7
            )

            if d < best_d:
                best_d = d
                best_i = i

            i += step

        # refine locally
        start = max(0, best_i - step)
        end = min(self.n - 1, best_i + step)

        i = start
        while i <= end:
            p = self.get_point(i)

            d = distance_2d_m(
                lat, lon,
                p[0] / 1e7,
                p[1] / 1e7
            )

            if d < best_d:
                best_d = d
                best_i = i

            i += 1

        return best_i            

    def get_next_d_km(self, lat, lon, d_km):

        start = self.find_closest_index(lat, lon)

        target = d_km * 1000
        acc = 0.0

        out = []

        prev = self.get_point(start)
        prev_lat = prev[0] / 1e7
        prev_lon = prev[1] / 1e7

        i = start

        while i < self.n:

            p = self.get_point(i)
            lat_i = p[0] / 1e7
            lon_i = p[1] / 1e7

            out.append((lat_i, lon_i, p[2]))

            if i > start:
                acc += distance_2d_m(prev_lat, prev_lon, lat_i, lon_i)

                if acc >= target:
                    break

            prev_lat = lat_i
            prev_lon = lon_i

            i += 1

        return out, i

