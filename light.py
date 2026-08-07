from geometry import *
from pyglet.shapes import Triangle

# What would a nice light jolt look like?
# Like the movement of candles, or old film

# And a light that affects color within

# Smoke
# Cold
# Fire
# Daylight

# Sharpness by shade darkness

# Light radius

class Light:
    # Obstacles must be shapes, as defined in the geometry module
    def __init__(self, center, obstacles, shadow_depth, batch):
        self.batch = batch
        self.center = center
        self.obstacles = obstacles
        self.shadow_depth = shadow_depth
        self.shadows = []

    def update(self, _):
        for shadow in self.shadows:
            del shadow
        self.shadows = []
        self.project()

    def project(self):
        for obstacle in self.obstacles:
            for start, end in self.facing_edges(obstacle):
                self.shadow(start, end)

    def facing_edges(self, shape):
        # An exposed edge is any edge in a shape that,
        # if you draw a segment from the light's center to the
        # edge, the intersection with other segments in the same shape
        # is empty (basically any edge you come across without running into another first)
        if isinstance(shape, Circle):
            # Add an edge
            ortho_vector = self.center.direction_vector(shape.center).ortho().scale(shape.radius)            
            begin = shape.center - ortho_vector
            end = shape.center + ortho_vector 
            return [(begin, end)]
        if isinstance(shape, Point):
            return []
        if isinstance(shape, Rectangle):
            Mx, My, mx, my = shape.maximal.x, shape.maximal.y, shape.minimal.x, shape.minimal.y 
            corners = [Point(Mx, My), Point(Mx, my), Point(mx, My), Point(mx, my)]
            edges = [(corners[3], corners[1]), (corners[1], corners[0]), (corners[0], corners[2]), (corners[2], corners[3])]
            corners = list(sorted(corners, key=(lambda x: self.center.distance(x))))
            # Leave out the farthest corner, irrelevant if a pair of corners is equally far
            closest_corners = corners[:-1]
            # Return the edges between the closest corners
            return list([e for e in edges if e[0] in closest_corners and e[1] in closest_corners])
        ## For arbitrary polygons, you sort vertices by distance.
        ## Then add any edge you can reach (in order) with a straight
        ## segment without crossing any segment you've already added

    def shadow(self, start, end):
        back_start = start + self.center.direction_vector(start).scale(self.shadow_depth)
        back_end = end + self.center.direction_vector(end).scale(self.shadow_depth)
        black = (0, 0, 0)
        self.shadows.append(Triangle(start.x, start.y, end.x, end.y, back_start.x, back_start.y, color=black, batch=self.batch))
        self.shadows.append(Triangle(back_start.x, back_start.y, back_end.x, back_end.y, end.x, end.y, color=black, batch=self.batch))

