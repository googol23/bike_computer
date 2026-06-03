from gpx_streamer import distance_2d_m, GPXStreamReader

class NavigationEngine:
    """
    Simple waypoint-based turn-by-turn navigation.
    Advances when user is close enough to next waypoint.
    """

    def __init__(self, rtepts, threshold_m=20):
        self.nav_pts = rtepts
        self.index = 0
        self.threshold_m = threshold_m

    def reset(self):
        self.index = 0

    def is_finished(self):
        return self.index >= len(self.nav_pts)

    def current_instruction(self):
        if self.is_finished():
            return None
        return self.nav_pts[self.index]

    @staticmethod
    def project_on_segment(ax, ay, bx, by, px, py):
        abx = bx - ax
        aby = by - ay
        apx = px - ax
        apy = py - ay

        ab_len2 = abx * abx + aby * aby
        if ab_len2 == 0:
            return 0.0

        t = (apx * abx + apy * aby) / ab_len2
        return max(0.0, min(1.0, t))

    @staticmethod
    def point_segment_distance(ax, ay, bx, by, px, py):
        t = NavigationEngine.project_on_segment(
            ax, ay, bx, by, px, py
        )

        proj_x = ax + t * (bx - ax)
        proj_y = ay + t * (by - ay)

        return distance_2d_m(
            px, py,
            proj_x, proj_y
        )

    def update_position(self, lat, lon) -> bool:
            if self.index >= len(self.nav_pts):
                return False
    
            old_index = self.index
            look_ahead_segments = 3
    
            start_seg = max(0, self.index - 1)
            end_seg = min(
                len(self.nav_pts) - 1,
                start_seg + look_ahead_segments
            )
    
            best_seg = start_seg
            best_dist = float("inf")
    
            for seg in range(start_seg, end_seg):
                a = self.nav_pts[seg]
                b = self.nav_pts[seg + 1]
    
                dist = self.point_segment_distance(
                    a["lat"], a["lon"],
                    b["lat"], b["lon"],
                    lat, lon
                )
    
                if dist < best_dist:
                    best_dist = dist
                    best_seg = seg
    
            # instruction is associated with segment end
            self.index = best_seg + 1
    
            return self.index != old_index




def draw_route_with_instructions(rtepts, show_numbers=True):
    """
    Visualize GPX route with navigation instructions.

    rtepts format:
    [{"lat":..., "lon":..., "desc":...}, ...]
    """
    import matplotlib.pyplot as plt

    if not rtepts:
        return

    lats = [p["lat"] for p in rtepts]
    lons = [p["lon"] for p in rtepts]

    plt.figure(figsize=(30, 30))

    # route line
    plt.plot(lons, lats, "-o")

    # annotations
    for i, p in enumerate(rtepts):
        label = p.get("desc", "")

        if show_numbers:
            label = f"{i}: {label}"

        plt.text(
            p["lon"],
            p["lat"],
            label,
            fontsize=8
        )

    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Route with Navigation Instructions")
    plt.grid(True)
    plt.gca().set_aspect('equal', adjustable='box')
    plt.savefig("route_with_instructions.png", dpi=300)
    
if __name__ == "__main__":
    streamer = GPXStreamReader("routes/arheilgen_to_ludwigsturm.gpx")
    streamer.load_navigation()
    # print(streamer.rtepts)
    
    nav = NavigationEngine(streamer.nav_pts)
    print(nav.nav_pts)
    # draw_route_with_instructions(nav.rtepts)