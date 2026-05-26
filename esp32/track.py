class Track:

    def __init__(self):
        self.points = []

    def add_point(self, lat, lon):
        self.points.append((lat, lon))

    def get_points(self):
        return self.points

    def clear(self):
        self.points = []

    def length(self):
        return len(self.points)

    def last_point(self):
        if not self.points:
            return None
        return self.points[-1]