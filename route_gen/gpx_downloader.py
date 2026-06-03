from datetime import datetime, timezone
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import json

from keys import GH_API_KEY

class GraphHopperAPI:
    def __init__(self, url, api_key):
        self.url = url
        self.api_key = api_key

        self.last_response = None

    def route(self, start_lat, start_lon, end_lat, end_lon):
        params = {
            "point": [
                f"{start_lat},{start_lon}",
                f"{end_lat},{end_lon}"
            ],
            "locale": "en",
            "instructions": "true",
            "profile": "bike",
            "elevation": "true",
            "points_encoded": "false",
            "via_point_instructions": "true",
            "type": "json",
            "key": self.api_key
        }

        response = requests.get(self.url, params=params)
        try:
            response.raise_for_status()
            self.last_response = response

            data = response.json()
            with open("route.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except:
            self.last_response = None
        
            
        return self.last_response
    
    def graphhopper_json_to_gpx(self, input_json: str | None = None,
                                output_file="route.gpx"):
    
        # -------------------------
        # LOAD DATA
        # -------------------------
        if input_json:
            with open(input_json, "r", encoding="utf-8") as f:
                data = json.load(f)
    
        elif self.last_response is not None:
            try:
                data = self.last_response.json()
            except Exception:
                data = json.loads(self.last_response.content.decode("utf-8"))
        else:
            print("No input data")
            return
    
        if "paths" not in data or not data["paths"]:
            print("Invalid response: no paths")
            return
    
        path = data["paths"][0]
        coords = path["points"]["coordinates"]
    
        # -------------------------
        # GPX ROOT
        # -------------------------
        gpx = ET.Element("gpx", {
            "version": "1.1",
            "creator": "YourRouteExporter",
            "xmlns": "http://www.topografix.com/GPX/1/1",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xmlns:gh": "https://graphhopper.com/public/schema/gpx/1.1"
        })
        
        # -------------------------
        # METADATA (proper GPX style)
        # -------------------------
        metadata = ET.SubElement(gpx, "metadata")
        
        copyright_tag = ET.SubElement(metadata, "copyright", {
            "author": "OpenStreetMap contributors"
        })
        
        # link = ET.SubElement(metadata, "link", {
        #     "href": "https://your-project-url.example"
        # })
        # ET.SubElement(link, "text").text = "Your GPX Route Exporter"
        
        ET.SubElement(metadata, "time").text = datetime.now(timezone.utc).isoformat()
    
        trk = ET.SubElement(gpx, "trk")
        trkseg = ET.SubElement(trk, "trkseg")
        rte = ET.SubElement(gpx, "rte")
    
        # -------------------------
        # TRACK POINTS (WITH ELEVATION ONLY HERE)
        # -------------------------
        for point in coords:
            lon, lat = point[0], point[1]
            ele = point[2] if len(point) > 2 else None
    
            trkpt = ET.SubElement(trkseg, "trkpt", {
                "lat": str(lat),
                "lon": str(lon)
            })
    
            if ele is not None:
                ET.SubElement(trkpt, "ele").text = str(ele)
    
        # -------------------------
        # NAVIGATION POINTS (NO ELEVATION)
        # -------------------------
        instructions = path.get("instructions", [])
    
        for instr in instructions:
            idx = instr["interval"][0]
        
            if idx >= len(coords):
                continue
        
            lon, lat = coords[idx][0], coords[idx][1]
        
            rtept = ET.SubElement(rte, "rtept", {
                "lat": f"{lat:.6f}",
                "lon": f"{lon:.6f}"
            })
        
            # EXACT desc format (web-style)
            ET.SubElement(rtept, "desc").text = instr.get("text", "")
        
            ext = ET.SubElement(rtept, "extensions")
        
            ET.SubElement(ext, "gh:distance").text = str(instr.get("distance", 0))
            ET.SubElement(ext, "gh:time").text = str(instr.get("time", 0))
            ET.SubElement(ext, "gh:sign").text = str(instr.get("sign", 0))
    
        # -------------------------
        # SAVE
        # -------------------------
        
        xml_str = ET.tostring(gpx, encoding="unicode")
        
        # manual formatting: split tags onto lines

        xml_str = xml_str.replace("<metadata>", "\n<metadata>\n")
        xml_str = xml_str.replace("</metadata>", "\n</metadata>\n")

        xml_str = xml_str.replace("<trk>", "<trk>\n")
        xml_str = xml_str.replace("</trk>", "</trk>\n")

        xml_str = xml_str.replace("</trkseg>", "</trkseg>\n")
        xml_str = xml_str.replace("<trkseg>", "<trkseg>\n")

        xml_str = xml_str.replace("<trkpt>", "<trkpt>\n")
        xml_str = xml_str.replace("</trkpt>", "</trkpt>\n")

        xml_str = xml_str.replace("<rte>", "<rte>\n")
        xml_str = xml_str.replace("</rte>", "</rte>\n")

        xml_str = xml_str.replace("<rtept>", "<rtept>\n")
        xml_str = xml_str.replace("</rtept>", "</rtept>\n")

        # tree = ET.ElementTree(gpx)
        # ET.indent(tree, space="\t", level=0)
        # tree.write(output_file, encoding="utf-8", xml_declaration=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(xml_str)
    
        print(f"Saved: {output_file}")
        

if __name__ == "__main__":
    gh_api = GraphHopperAPI("https://graphhopper.com/api/1/route", GH_API_KEY)
    
    start_lat, start_lon = 49.901106,8.657435
    end_lat, end_lon = 50.085573,8.910603
    # gh_api.route(start_lat, start_lon, end_lat, end_lon)

    gh_api.graphhopper_json_to_gpx("route.json")

