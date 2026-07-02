from math import sqrt, dist
from json import dumps
from numbers import Number
from math import acos
from math import cos, sin
from math import pi
from random import uniform

## This module does not support operations requiring high numeric precision
## Its intended use case is () 2D vectors with integer coordinates

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
    if clip:                          # if projection is not on line segment
        if rid > d:                   # clip to endpoints if clipToSegment set
            return r1
        if rid < 0:
            return r0
    return lpt

def segment_within_distance(p, q, a, d):
    return int(d) - int(nearest_point_on_segment(a, p, q).distance(a)) > -1
    
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
        raise Exception("Argument 'other' of Circle.collides(other) must be a Circle, Point, or Rectangle.")
    
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
        raise Exception("Argument 'other' of Rectangle.collides(other) must be a Circle, Point, or Rectangle.")
    
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
        if isinstance(other, Point):
            return self.x == other.x and self.y == other.y
        raise Exception("Argument 'other' of Point.collides(other) must be a Circle, Point, or Rectangle.")

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
    
'float, not {type(value)}'
