BLACK   = 0x0000
WHITE   = 0xFFFF
RED     = 0xF800
GREEN   = 0x07E0
BLUE    = 0x001F
YELLOW  = 0xFFE0
CYAN    = 0x07FF
MAGENTA = 0xF81F

import math

class MapRenderer:

    def __init__(self, width, height, draw_pixel, clear_screen):

        self.width = width
        self.height = height

        self.draw_pixel = draw_pixel
        self.clear_screen = clear_screen

        self.center_lat = 0.0
        self.center_lon = 0.0

        self.scale = 1000000

        # previous marker screen position
        self.prev_x = None
        self.prev_y = None

        # previous GPS position
        self.prev_lat = None
        self.prev_lon = None

    # ------------------------------------------
    # set map center
    # ------------------------------------------
    def set_center(self, lat, lon):
        self.center_lat = lat
        self.center_lon = lon

    # ------------------------------------------
    # GPS -> screen coordinates
    # ------------------------------------------
    def project(self, lat, lon):
    
        # Earth approximation
        meters_per_deg_lat = 111320
        meters_per_deg_lon = 111320 * math.cos(self.center_lat * 0.0174533)
    
        dy = (lat - self.center_lat) * meters_per_deg_lat
        dx = (lon - self.center_lon) * meters_per_deg_lon
    
        # tuning factor (zoom)
        zoom = 0.5  # increase = more zoomed in
    
        sx = int(self.width // 2 + dx * zoom)
        sy = int(self.height // 2 - dy * zoom)
    
    
        print("SCREEN", sx, sy)
        
        return sx, sy

    
    # ------------------------------------------
    # draw marker
    # ------------------------------------------
    def draw_marker(self, x, y, color):

        for dx in (-2, -1, 0, 1, 2):
            for dy in (-2, -1, 0, 1, 2):

                px = x + dx
                py = y + dy

                if 0 <= px < self.width and 0 <= py < self.height:
                    self.draw_pixel(px, py, color)

    # ------------------------------------------
    # Bresenham line
    # ------------------------------------------
    def draw_line(self, x0, y0, x1, y1, color):

        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1

        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1

        err = dx + dy

        while True:

            if 0 <= x0 < self.width and 0 <= y0 < self.height:
                self.draw_pixel(x0, y0, color)

            if x0 == x1 and y0 == y1:
                break

            e2 = err * 2

            if e2 >= dy:
                err += dy
                x0 += sx

            if e2 <= dx:
                err += dx
                y0 += sy

    # ------------------------------------------
    # incremental rendering
    # ------------------------------------------
    def update(self, lat, lon):

        # project current GPS point
        x, y = self.project(lat, lon)

        # erase old marker
        if self.prev_x is not None:
            self.draw_marker(self.prev_x, self.prev_y, BLACK)

        # draw newest track segment
        if self.prev_lat is not None:

            x0, y0 = self.project(self.prev_lat, self.prev_lon)

            self.draw_line(x0, y0, x, y, WHITE)

        # draw new marker
        self.draw_marker(x, y, RED)

        # store previous values
        self.prev_x = x
        self.prev_y = y

        self.prev_lat = lat
        self.prev_lon = lon