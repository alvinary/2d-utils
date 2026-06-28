from random import uniform
from random import randint
from random import choice
from math import sin, floor
from itertools import product
from json import loads

from geometry import *

base_grid = [(i, j) for i in range(0, 5) for j in range(0, 5)]
radiuses = [0.5, 1, 1.5, 2, 2.5]
scales = [1, 2, 3]

left = Point(-1, 0)
middle = Point(0, 0)
right = Point(1, 0)
up = Point(0, 1)
down = Point(0, -1)

lalo = Rectangle(down + left, right + up)
balo = Rectangle(middle, up.scale(2) + right.scale(2))


def test_point_arithmetic():
    assert left + middle == left
    assert left + left == Point(-2, 0)
    assert Point(2, 0) - right - right - up == down
    assert right + up == Point(1, 1)
    assert right.scale(2) == right + right
    assert right.norm() == 1
    assert right.scale(2).norm() == 2
    assert (right.scale(2) + up.scale(2)).norm() == sqrt(8)

def test_scaling():
    for x, y in product(range(0, 300), range(0, 300)):
        point = Point(x, y)
        assert point.scale(2).distance(middle) == point.norm() * 2

def test_rectangle_center():
    assert lalo.center() == middle
    assert balo.center() == up + right

def test_circle_collisions():
    poochi = Circle(middle, 1)
    moochi = Circle(right.scale(2), 1)
    assert poochi.collides(moochi)
    moochi.radius = 0.5
    assert not poochi.collides(moochi)
    moochi.radius = 1
    moochi.center.x = 3
    assert not poochi.collides(moochi)
    poochi.radius = 5
    assert moochi.collides(poochi)

def test_direction_vectors():
    assert middle.direction_vector(up) == up
    chochi = up + up + right + right
    print(chochi)
    print((up + right).scale(chochi.norm()))
    print(middle.direction_vector(chochi))
    assert middle.direction_vector(chochi) == middle.direction_vector(up + right)
    assert middle.direction_vector(chochi + right + right) == middle.direction_vector(up + right + right)
    assert middle.direction_vector(up + right) == (up + right).direction_vector(chochi)
    assert chochi.direction_vector(right + up) == middle.direction_vector(left + down)
    assert middle.direction_vector(chochi).scale(chochi.norm()) == chochi 

def test_straight_square_distances():
    max_corner = Point(90, 120)
    min_corner = Point(60, 90)
    square = Rectangle(min_corner, max_corner)
    above_straight = Point(75, 150)
    above_diagonal = Point(100, 130)
    inside = Point(75, 105)
    assert above_straight.distance(square) == 30
    assert above_diagonal.distance(square) == sqrt(10**2 + 10**2)
    assert inside.distance(square) <= 0
    assert square.center() == inside

def test_gauging():
    first = Point(20, 30)
    second = Point(40, 60)
    dist = first.distance(second)
    assert first.distance(first.middle(second, 0)) == 0
    assert first.distance(first.middle(second, 1)) == first.distance(second)
    assert first.distance(first.middle(second, 0.5)) == first.distance(second) / 2
    assert first + first.direction_vector(second).scale(dist / 2) == first.middle(second, 0.5)

def test_saving():
    squero = Rectangle(down + left, up + right)
    cerclo = Circle(middle, 20)
    squero_dict = loads(str(squero))
    assert squero_dict['minimal']['x'] == squero.minimal.x
    assert squero_dict['maximal']['y'] == squero.maximal.y
    assert squero_dict['type'] == 'Rectangle'
    assert squero_dict['minimal']['type'] == 'Point'
    squero_dict_b = squero.save()
    # Compare squero a and squero b

def test_ortho():
    for i in range(4):
        x = choice([-3, -2, -1, 0, 1, 2, 3])
        y = choice([-3, -2, -1, 1, 2, 3])
        point = Point(x, y)
        assert point.x * point.ortho().x + point.y * point.ortho().y == 0

def test_nearest():
    zero = Point(0, 0)
    one = Point(1, 0)
    one_bit = Point(1.2, 0)
    assert nearest_point_on_segment(one_bit, zero, one) == one
    assert abs((one_bit - nearest_point_on_segment(one_bit, zero, one)).norm() - 0.2) <= 0.001
    assert abs(nearest_point_on_segment(one_bit, zero, one).distance(one_bit) - 0.2) <= 0.001

def test_within_distance():
    corner = Point(8, 8)
    for i in range(25):
        # Choose two random points
        q = Point(randint(-8, 8), randint(-8, 8))
        p = Point(randint(-8, 8), randint(-8, 8))
        # p, q = min_point(p, q), max_point(p, q)
        # Choose a random distance from 1 to the norm of <20, 20>
        distance = uniform(0.0, corner.norm())
        # Test four random points inside
        for i in range(0, 4):
            p_to_q = uniform(0.0, 1.0)
            # Choose a point between p and q
            within = p + p_to_q * (q - p).norm() * p.direction_vector(q)
            # Add to it a random orthogonal vector whose norm is less than 'distance'
            length = uniform(0.0, distance)
            within = within + length * (q - p).ortho().unit()
            within = Point(int(within.x), int(within.y))
            print(p)
            print(q)
            print(within)
            print(length)
            print(int(line_distance(p, q, within)))
            assert length <= distance
            assert int(nearest_point_on_segment(within, p, q).distance(within)) - int(length) <= 1
        # Test four random points outside
        for i in range(0, 4):
            p_to_q = uniform(0.0, 1.0)
            # Choose a point between p and q
            not_within = p + p_to_q * (q - p).norm() * p.direction_vector(q)
            # Add to it a random orthogonal vector whose norm is greater than 'distance'
            length = uniform(distance + 0.3, distance * 2)
            not_within = not_within + length * (q - p).ortho().unit()
            not_within = Point(int(not_within.x), int(not_within.y))
            print(p)
            print(q)
            print(not_within)
            print(length)
            print(int(line_distance(p, q, not_within)))
            assert length > distance
            assert int(nearest_point_on_segment(within, p, q).distance(within)) - int(length) <= 1
