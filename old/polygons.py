from defs import main_batch
from defs import transparent_blue, transparent_green
from defs import LONG_SEGMENT_LENGTH, line_collision
from pyglet.shapes import Line, Rectangle

from cursor import cursor

def point_in_polygon(x, y, polygon):
    # Implementation taken from Geeks for Geeks
    num_vertices = len(polygon)
    inside = False
    # Store the first point in the polygon and initialize the second point
    p1_x, p1_y = polygon[0]
    # Loop through each edge in the polygon
    for i in range(1, num_vertices + 1):
        # Get the next point in the polygon
        p2_x, p2_y = polygon[i % num_vertices]
        # Check if the point is above the minimum y coordinate of the edge
        if y > min(p1_y, p2_y):
            # Check if the point is below the maximum y coordinate of the edge
            if y <= max(p1_y, p2_y):
                # Check if the point is to the left of the maximum x coordinate of the edge
                if x <= max(p1_x, p2_x):
                    # Calculate the x-intersection of the line connecting the point to the edge
                    x_intersection = (y - p1_y) * (p2_x - p1_x) / (p2_y - p1_y) + p1_x
                    # Check if the point is on the same line as the edge or to the left of the x-intersection
                    if p1_x == p2_x or x <= x_intersection:
                        # Flip the inside flag
                        inside = not inside
        # Store the current point as the first point for the next iteration
        p1_x, p1_y = p2_x, p2_y
    # Return the value of the inside flag
    return inside

class Polygon:

    def __init__(self, vertices, traits, color=False):

        self.vertices = vertices
        self.shape_vertices = list(vertices)
        self.traits = []
        if traits:
            self.traits = list(traits)
        self.x, self.y = self.vertices[0]
        self.x_side = 10
        self.y_side = 10
        self.shapes = []
        self.time = 0.3
        if not color:
            color = (255, 0, 0)
        self.color = color
        self.compose_shape()
        self.handlers = [self]
        self.live = True

    def update(self, dt):
        if self.time < 0:
            self.color = transparent_blue
            self.time = 0.3
            for shape in self.shapes:
                shape.color = transparent_blue
        if self.time >= 0 and self.color == transparent_green:
            self.time -= dt

    def point_collision(self, x, y):
        return point_in_polygon(x, y, self.vertices)
    
    def jordan_point_collision(self, x, y):
        # Should be equivalent to point_collision, while being more readable, but I haven't properly tested it
        num_vertices = len(self.vertices)
        collision_count = 0
        p1 = (x, y)
        q1 = (x + LONG_SEGMENT_LENGTH, y)
        for index in range(num_vertices):
            p2 = self.vertices[index]
            q2 = self.vertices[(index + 1) % num_vertices]
            collision_count += line_collision(p1, q1, p2, q2)
        if collision_count % 2 == 0:
            return False
        if collision_count % 2 == 1:
            return True

    def check_collision(self, target):
        return self.point_collision(target.x, target.y)

    def collide(self, target):
        self.color = (255, 0, 0)
        for shape in self.shapes:
            shape.color = (0, 0, 255)

    def compose_shape(self):
        num_vertices = len(self.vertices)
        for index in range(num_vertices):
            x, y = self.shape_vertices[index]
            x1, y1 = self.shape_vertices[(index + 1) % num_vertices]
            tip1 = Rectangle(x, y, 10, 10, color=self.color, batch=main_batch)
            tip2 = Rectangle(x1, y1, 10, 10, color=self.color, batch=main_batch)
            edge = Line(x,
                        y,
                        x1,
                        y1,
                        width=1,
                        color=self.color,
                        batch=main_batch)
            self.shapes.append(edge)
            self.shapes.append(tip1)
            self.shapes.append(tip2)

    def move_shape(self, dx, dy):
        for shape in self.shapes:
            shape.x -= dx
            shape.y -= dy

    def delete(self):
        self.live = False
        for shape in self.shapes:
            del shape
        del self
