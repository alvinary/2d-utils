from itertools import product
from math import sqrt
from collections import defaultdict
from functools import cache

from tags import BLOCKED
from defs import distance
from defs import DEFAULT_SPRITE_WIDTH as CHARACTER_WIDTH
from defs import CHARACTER_SCALE

TERRAIN_INTERVAL = 24

def get_whole_area(polygons):
    max_x = 0
    max_y = 0
    min_x = 2**40
    min_y = 2**40
    for p in polygons:
        max_x = max(max_x, max([x for x, y in p.vertices]))
        max_y = max(max_y, max([y for x, y in p.vertices]))
        min_x = min(min_x, min([x for x, y in p.vertices]))
        min_y = min(min_y, min([y for x, y in p.vertices]))
    return min_x, min_y, max_x, max_y


@cache
def nearest(x, y):
    hypo = sqrt(TERRAIN_INTERVAL**2 + TERRAIN_INTERVAL**2)
    return [(x + TERRAIN_INTERVAL, y, TERRAIN_INTERVAL),
            (x - TERRAIN_INTERVAL, y, TERRAIN_INTERVAL),
            (x, y + TERRAIN_INTERVAL, TERRAIN_INTERVAL),
            (x, y - TERRAIN_INTERVAL, TERRAIN_INTERVAL) ]
    '''
            [
            (x - TERRAIN_INTERVAL, y - TERRAIN_INTERVAL, hypo),
            (x - TERRAIN_INTERVAL, y + TERRAIN_INTERVAL, hypo),
            (x + TERRAIN_INTERVAL, y - TERRAIN_INTERVAL, hypo),
            (x + TERRAIN_INTERVAL, y + TERRAIN_INTERVAL, hypo)
            ]
    '''

def map_grid(polygons):
    ox, oy, w, h = get_whole_area(polygons)
    vertices = set()
    xs = range(0, int(w), TERRAIN_INTERVAL)
    ys = range(0, int(h), TERRAIN_INTERVAL)
    for x, y in product(xs, ys):
        vertices.add((x, y))
    all = set(vertices)
    for p in polygons:
        for v in vertices:
            x, y = v
            if p.point_collision(x, y):
                all.discard(v)
    return all

def clip(x, y):
    x = round(x / TERRAIN_INTERVAL) * TERRAIN_INTERVAL
    y = round(y / TERRAIN_INTERVAL) * TERRAIN_INTERVAL
    return (x, y)

class TerrainGraph:

    def __init__(self, target_map, from_rects=False):

        self.map = target_map
        self.rectangles = []
        self.area_parts = [p for p in self.map.polygons if BLOCKED in p.traits]

        if from_rects:
            for r in self.map.rectangles:
                self.rectangles.append(r)
                print('rectangles: ')
                for r in self.rectangles:
                    r1, r2, r3, r4 = r
                    ox, oy, cx, cy = int(r1), int(r2), int(r3 + r1), int(r4 + r3)
                    print(ox, oy, cx, cy)
                print('---' * 10)

        self.vertices = map_grid(self.area_parts)

        if from_rects:
            def within(x, y, r):
                r1, r2, r3, r4 = r
                ox, oy, cx, cy = int(r1), int(r2), int(r3 + r1), int(r2 + r4)
                return ox <= x and x <= cx and oy <= y and y <= cy
            self.vertices = []
            xs = range(0, int(600), TERRAIN_INTERVAL)
            ys = range(0, int(600), TERRAIN_INTERVAL)
            for x, y in product(xs, ys):
                if True not in [within(x, y, r) for r in self.rectangles]:
                    self.vertices.append((x, y))
            print('nv: ', len(self.vertices))

        self.upper_bound = 999999999**2
        self.neighbors = defaultdict(lambda: [])
        self.paths = defaultdict(lambda: [])
        self.costs = defaultdict(lambda: self.upper_bound)

        for x1, y1 in self.vertices:
            for x2, y2, c in nearest(x1, y1):
                if (x2, y2) in self.vertices:
                    # Si no hay un poligono que trabe una linea entre (x1, y2) y (x2, y2)...
                    self.neighbors[(x1, y1)].append((x2, y2))
                    self.paths[(x1, y1), (x2, y2)] = [(x1, y1), (x2, y2)]
                    self.costs[(x1, y1), (x2, y2)] = c

    # Esto usa bastante memoria y es lento para grids muy finas
    # Para TERRAIN_INTERVAL >= 10 anda re bien
    def get_path(self, source, target):
        visited = set()
        source = clip(*source)
        target = clip(*target)
        queue = [source]
        queue_additions = set(queue)
        while queue and (source, target) not in self.paths:
            current = queue.pop(0)
            new_neighbors = [
                n for n in self.neighbors[current]
                if n not in visited and n not in queue_additions
            ]
            for neighbor in new_neighbors:
                if self.costs[source, current] + self.costs[
                        current, neighbor] < self.costs[source, neighbor]:
                    self.paths[source, neighbor] = list(self.paths[source,
                                                                   current])
                    self.paths[source, neighbor].append(neighbor)
                    self.costs[source, neighbor] = self.costs[
                        source, current] + self.costs[current, neighbor]
                if neighbor not in visited:
                    queue.append(neighbor)
                    queue_additions.add(neighbor)
            visited.add(current)
        return (self.paths[source, target], self.costs[source, target])
        
    def get_reachable(self, source, max_distance):
        source = clip(*source)
        queue = [source]
        distances = {}
        distances[source] = 0
        visited = set([source])
        reachable_vertices = set()
        while queue:
            current = queue.pop(0)
            reachable_vertices.add(current)
            neighbors = [n for n in self.neighbors[current] if n not in visited]
            for neighbor in neighbors:
                new_distance = distances[current] + distance(*current, *neighbor)
                if neighbor in distances:
                    new_distance = min(distances[neighbor], new_distance)
                if new_distance <= max_distance:
                    distances[neighbor] = new_distance
                    reachable_vertices.add(neighbor)
                    queue.append(neighbor)
                visited.add(neighbor)
        return reachable_vertices
        
