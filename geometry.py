from math import sqrt, dist
from json import dumps
from numbers import Number
from math import acos
from math import cos, sin
from math import pi
from random import uniform

## This module does not support operations requiring high numeric precision
## Its intended use is limited to operations with 2D vectors with integer coordinates for 2D games

def check_type(name, signature, expected_type, expected_type_name, actual_value):
    if not isinstance(actual_value, expected_type):
        message = f"Argument {name} of {signature} must be an instance of '{expected_type_name}'."
        specifics = f"\nHowever, the argument provided was {type(actual_value)}"
        raise Exception(message + specifics)

def line_distance(p, q, a):
    return (abs(q.x - p.x) * (p.y - a.y) - (p.x - a.x) * (q.y - p.y)) / sqrt((q.x - p.x)**2 + (q.y - p.y)**2)

def nearest_point_on_segment(pt, r0, r1, clip=True):
    # Taken from user Andrew's reply in https://stackoverflow.com/questions/910882/how-can-i-tell-if-a-point-is-nearby-a-certain-line
    r01 = r1 - r0                     # vector from r0 to r1 
    d = r01.norm()                    # length of r01
    r01u = r0.direction_vector(r1)    # unit vector from r0 to r1
    r = pt - r0                       # vector from r0 to pt
    rid = r.x * r01u.x + r.y * r01u.y # projection (length) of r onto r01u
    ri = rid * r01u                   # projection vector
    lpt = r0 + ri                     # point on line
    if clip:                          # if projection is not on line segment, clip to endpoints if clip is set to True
        if rid > d:                   
            return r1
        if rid < 0:
            return r0
    return lpt

def segment_within_distance(p, q, a, d):
    return int(d) - int(nearest_point_on_segment(a, p, q).distance(a)) > -1

# Segment intersection

def orientation(p, q, r):
    px, py = p.x, p.y
    qx, qy = q.x, q.y
    rx, ry = r.x, r.y
    result = (qy - py) * (rx - qx) - (qx - px) * (ry - qy)
    if result > 0:
        orientation = 1
    if result < 0:
        orientation = 2
    if result == 0:
        orientation = 0
    return orientation

def on_segment(p, q, r):
    return q.x <= max(p.x, r.x) and q.x >= min(p.x, r.x) and q.y <= max(p.y, r.y) and q.y >= min(p.y, r.y)

def segments_intersect(p1, q1, p2, q2):
    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)
    if ((o1 != o2) and (o3 != o4)):
        return True
    if ((o1 == 0) and on_segment(p1, p2, q1)):
        return True
    if ((o2 == 0) and on_segment(p1, q2, q1)):
        return True
    if ((o3 == 0) and on_segment(p2, p1, q2)):
        return True
    if ((o4 == 0) and on_segment(p2, q1, q2)):
        return True
    return False

# Point within triangle

def get_side_sign(p1, p2, p3):
    return (p1.x - p3.x) * (p2.y - p3.y) - (p2.x - p3.x) * (p1.y - p3.y)

def triangle_contains_point(traingle_vertices, point):
    v1, v2, v3 = traingle_vertices
    pt = point
    d1 = get_side_sign(pt, v1, v2)
    d2 = get_side_sign(pt, v2, v3)
    d3 = get_side_sign(pt, v3, v1)
    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)

# Module classes proper
    
class Circle:

    def __init__(self, center, radius):

        self.center = center
        self.radius = radius

        check_type('center', 'Circle(center, radius)', Point, 'Point', center)
        check_type('radius', 'Circle(center, radius)', Number, 'Number', radius)

        if self.radius <= 0:
            message = "Argument 'radius' of Circle(center, radius) must be greater than zero."
            specifics = f"\nHowever, the argument provided was {radius}."
            raise Exception(message + specifics)
        
    def __str__(self):
        return dumps(self.save())

    def move(self, x, y):
        self.center = Point(x, y)

    def distance(self, other):
        if isinstance(other, Point):
            return self.center.distance(other) - self.radius
        if isinstance(other, Circle):
            return self.center.distance(other.center) - self.radius - other.radius
        if isinstance(other, Rectangle):
            if other.collides(self.center):
                return 0
            else:
                return self.center.distance(other) - self.radius
        raise Exception("Argument 'other' of Circle.distance(other) must be a Circle, Point or Rectangle.")
        
    def collides(self, other):
        if isinstance(other, Point) or isinstance(other, Circle):
            return self.distance(other) <= 0
        if isinstance(other, Rectangle):
            return other.collides(self)
        if isinstance(other, Triangle):
            return other.collides(self)
        if isinstance(other, Segment):
            return other.collides(self)
        raise Exception("Argument 'other' of Circle.collides(other) must be a Circle, Point, Rectangle, Segment or Triangle.")
    
    def save(self):
        return {
            'type': 'Circle', 
            'center': self.center.save(), 
            'radius': self.radius
        }
    
class Rectangle:

    def __init__(self, minimal_corner, maximal_corner):
        
        self.maximal = maximal_corner
        self.minimal = minimal_corner

        check_type('minimal_corner', 'Rectangle(minima_corner, maximal_corner)', Point, 'Point', minimal_corner)
        check_type('maximal_corner', 'Rectangle(minima_corner, maximal_corner)', Point, 'Point', maximal_corner)
        
        if not self.minimal.x < self.maximal.x or not self.minimal.y < self.maximal.y:
            raise Exception('A Rectangle must have a minimal corner that is pointwise strictly smaller than its maximal corner')

    def __str__(self):
        return dumps(self.save())

    def move(self, x, y):
        dx = x - (self.minimal.x + (self.maximal.x - self.minimal.x) / 2)
        dy = y - (self.minimal.y + (self.maximal.y - self.minimal.y) / 2)
        self.maximal = Point(self.maximal.x + dx, self.maximal.y + dy)
        self.minimal = Point(self.minimal.x + dx, self.minimal.y + dy)
    
    # TODO: define for segments
    def distance(self, other):
        if isinstance(other, Rectangle):
            return 0
        if isinstance(other, Point) or isinstance(other, Circle):
            return other.distance(self)
        else:
            raise Exception("Argument 'other' in Rectangle.distance(other) must be a Circle, Point, or Rectangle")

    def collides(self, other):
        if isinstance(other, Point):
            check_x = other.x >= self.minimal.x and other.x <= self.maximal.x
            check_y = other.y >= self.minimal.y and other.x <= self.maximal.y
            return check_x and check_y
        if isinstance(other, Rectangle):
            entirely_right = self.minimal.x > other.maximal.x
            entirely_left = self.maximal.x < other.minimal.x
            entirely_above = self.minimal.y > other.maximal.y
            entirely_below = self.maximal.y < other.minimal.y
            return not (entirely_right or entirely_below or entirely_left or entirely_above)
        if isinstance(other, Circle):
            return self.collides(other.center) or (other.center.distance(self) < other.radius)
        if isinstance(other, Triangle):
            return other.collides(self)
        if isinstance(other, Segment):
            return other.collides(self)
        raise Exception("Argument 'other' of Rectangle.collides(other) must be a Circle, Point, Rectangle, Triangle, or Segment.")
    
    def center(self):
        bottom_right = Point(self.maximal.x, self.minimal.y)
        top_left = Point(self.minimal.x, self.maximal.y)
        middle_x = self.minimal.x + self.minimal.distance(bottom_right) / 2
        middle_y = self.minimal.y + self.minimal.distance(top_left) / 2
        return Point(middle_x, middle_y)

    def save(self):
        return {
            'type' : 'Rectangle',
            'minimal' : self.minimal.save(),
            'maximal' : self.maximal.save()
        }

class Segment:

    def __init__(self, begin, end):
        self.begin = begin
        self.end = end

    def __str__(self):
        return dumps(self.save())

    def __eq__(self, other):
        if not isinstance(other, Segment):
            return False
        return (self.begin == other.begin and self.end == other.end) or (self.begin == other.end and self.end == other.begin)

    def save(self):
        return {
            'type' : 'Triangle',
            'begin' : self.begin.save(),
            'end' : self.end.save()
        }

    def length(self):
        return (self.end - self.begin).norm()

    def collides(self, other):
        if isinstance(other, Circle):
            # True if the point lying on the segment that's closest
            # to the center of the circle is within 'other.radius' of it
            return nearest_point_on_segment(other.center, self.begin, self.end).distance(other.center) <= other.radius
        if isinstance(other, Rectangle):
            # True if any of the segment ends is inside the rectangle, 
            # or any side of the rectangle intersects with the segment
            if other.collides(self.begin) or other.collides(self.end):
                return True
            mx, my = other.minimal.x, other.minimal.y
            Mx, My = other.maximal.x, other.maximal.y
            edges = ([Segment(Point(mx, my), Point(Mx, my)), 
                      Segment(Point(Mx, my), Point(Mx, My)), 
                      Segment(Point(Mx, My), Point(mx, My)),
                      Segment(Point(mx, My), Point(mx, my))])
            return any([self.collides(edge) for edge in edges])
        if isinstance(other, Point):
            return (self.begin.x <= max(other.x, self.end.x) and 
                    self.begin.x >= min(other.x, self.end.x) and 
                    self.begin.y <= max(other.y, self.end.y) and 
                    self.begin.y >= min(other.y, self.end.y))
        if isinstance(other, Segment):
            return segments_intersect(self.begin, self.end, other.begin, other.end)
        if isinstance(other, Triangle):
            return other.collides(self)
        raise Exception("Argument 'other' of Segment.collides(other) must be a Circle, Point, Rectangle, Segment or Triangle.")

class Triangle:

    def __init__(self, vertices):
        self.vertices = vertices

        three_elements = len(self.vertices) == 3
        all_points = all([isinstance(v, Point) for v in vertices])
        if not three_elements and all_points:
            error_message = "A Triangle must be initialized by supplying a list with exactly three points.\n"
            error_message += "The argument supplied, however,\n"
            if not three_elements:
                error_message += "...was of length {len(self.vertices)}.\n"
            if not all_points:
                error_message += "...contained instances of other clases: " + ", ".join([str(type(v) for v in vertices)])
            raise Exception(error_message)

    def __str__(self):
        pass

    def __eq__(self, other):
        if not isinstance(other, Triangle):
            return False
        return set([(p.x, p.y) for p in self.vertices]) == set([(p.x, p.y) for p in other.vertices])

    def collides(self, other):
        if isinstance(other, Circle):
            # If the center is inside the triangle, the shapes collide
            if self.collides(other.center):
                return true
            # If the center is outside the triangle, then there must be an edge that's the closest to it. 
            # That edge has a point closest to the center, and the shapes collide if the distance is less or equal than the radius
            first, second, _ = sorted(self.vertices, lambda x: distance(x, other.center))
            closest_point = nearest_point_on_segment(other.center, first, second)
            return (other.center - closest_point).norm() <= other.radius
        if isinstance(other, Rectangle):
            # True if any of the edges of self and other intersect,
            # or if any of the vertices of the triangle is contained
            # in the rectangle
            vertices_inside = [v for v in self.vertices if other.collide(v)]
            if vertices_inside:
                return True
            v1, v2, v3 = self.vertices
            triangle_edges = [Segment(v1, v2), Segment(v2, v3), Segment(v3, v1)] # Maybe it'd be best to just have the edges, to avoid computing them every time
            mx, my = other.minimal.x, other.minimal.y
            Mx, My = other.maximal.x, other.maximal.y
            rectangle_edges = ([Segment(Point(mx, my), Point(Mx, my)), 
                      Segment(Point(Mx, my), Point(Mx, My)),
                      Segment(Point(Mx, My), Point(mx, My)),
                      Segment(Point(mx, My), Point(mx, my))])
            collisions = False
            for edge in triangle_edges:
                collisions = collisions or any([edge.collide(e) for e in rectangle_edges])
            return collisions
        if isinstance(other, Point):
            # Defined in an auxiliary function
            return triangle_contains_point(self.vertices, other)
        if isinstance(other, Segment):
            # True if any of the segments ends is within the triangle
            # or the segment intersects with any of the edges
            return False
        if isinstance(other, Triangle):
            # True if... sigh... any... of... the vertices is within the other triangle,
            # or any pair of edges collide
            return False
        raise Exception("Argument 'other' of Segment.collides(other) must be a Circle, Point, Rectangle, Segment or Triangle.")

    def move(self, x, y):
        pass

    def distance(self, other):
        pass

    def collide(self, other):
        pass
        
     
class Point:

    def random(begin=0.0, end=4*pi):
        angle = uniform(begin, end)
        return Point(cos(angle), sin(angle))

    def __init__(self, x, y):
        self.x = x
        self.y = y
        check_type('x', 'Point(x, y)', Number, 'Number', x)
        check_type('y', 'Point(x, y)', Number, 'Number', y)

    def __str__(self):
        return dumps(self.save())

    def __eq__(self, other):
        if not isinstance(other, Point):
            return False
        else:
            return self.x == other.x and self.y == other.y

    def __add__(self, other):
        if isinstance(other, Point):
            return Point(self.x + other.x, self.y + other.y)
        raise Exception("Argument 'other' of Point.__add__(other) must be a Point.")
    
    def __sub__(self, other):
        if isinstance(other, Point):
            return Point(self.x - other.x, self.y - other.y)
        raise Exception("Argument 'other' of Point.__sub__(other) must be a Point.")

    def __rmul__(self, other):
        if isinstance(other, Number):
            return Point(self.x * other, self.y * other)
        raise Exception(f"Argument 'other' of Point.__rmul__(other) must be a Number. Here, 'other' was a {str(type(other))}")

    def move(self, x, y):
        self.x = x
        self.y = y

    def norm(self):
        return sqrt(self.x ** 2 + self.y ** 2)

    def ortho(self):
        return Point(-self.y, self.x)

    def unit(self):
        return self.scale(1 / self.norm())
    
    def scale(self, scalar):
        if type(scalar) in [type(4), type(2.5)]:
            return Point(self.x * scalar, self.y * scalar)
        raise Exception("Argument 'scalar' of Point.scale(scalar) must be an Int or Float.")
    
    def direction_vector(self, other):
        difference = other - self
        return difference.scale(1 / difference.norm())

    def collides(self, other):
        if isinstance(other, Circle):
            return other.collides(self)
        if isinstance(other, Rectangle):
            return other.collides(self)
        if isinstance(other, Triangle):
            return other.collides(self)
        if isinstance(other, Segment):
            return other.collides(self)
        if isinstance(other, Point):
            return self.x == other.x and self.y == other.y
        raise Exception("Argument 'other' of Point.collides(other) must be a Circle, Point, Rectangle, Segment, or Triangle.")

    def distance(self, other):
        if isinstance(other, Point):
            return sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
        if isinstance(other, Circle):
            return self.distance(other.center) - other.radius
        if isinstance(other, Rectangle):
            clamped_x = max(other.minimal.x, min(self.x, other.maximal.x))
            clamped_y = max(other.minimal.y, min(self.y, other.maximal.y))
            closest_point = Point(clamped_x, clamped_y)
            return self.distance(closest_point)
        raise Exception("Argument other of Point.distance(other) must be a Point or a Circle.")

    def least(self, other):
        origin = Point(0, 0)
        if origin.distance(self) < origin.distance(other):
            return self
        else:
            return other

    def greatest(self, other):
        origin = Point(0, 0)
        if origin.distance(self) >= origin.distance(other):
            return self
        else:
            return other
    
    def middle(self, other, gauge):
        if isinstance(gauge, Number) and isinstance(other, Point):
            if gauge > 1 or gauge < 0:
                raise Exception("Argument 'gauge' of Point.middle(other, gauge) must be a real number between 0 and 1.")
            distance = self.distance(other) * gauge
            displacement = self.direction_vector(other).scale(distance)
            return self + displacement
        raise Exception("Arguments 'other' and 'gauge' of Point.middle(other, gauge) must be Point and Float, respectively.")

    def angle(self, other):
        scalar_product = self.x * other.x + self.y * other.y
        norms_product = self.norm() * other.norm()
        return acos(scalar_product / norms_product)

    def rotate(self, angle):
        rotated_x = self.x * cos(angle) - self.y * sin(angle)
        rotated_y = self.x * sin(angle) + self.y * cos(angle)
        return Point(rotated_x, rotated_y)

    def save(self):
        return {
            'type': 'Point', 
            'x': self.x, 
            'y': self.y
        }
