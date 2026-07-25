from itertools import product

from engine_constants import TILE_SIDE, SCALE, OBSTACLE, DIFFICULT_TERRAIN, BASE_COST, NOTHING, LARGE_VALUE

class TerrainBlock:

    def __init__(self, height, width, terrain_elements):
        # Assumes 'terrain elements' are snapped to the grid
        self.costs = {}
        self.base_next = {}
        self.deviations = set()
        self.current_next = {}
        self.terrain_elements = terrain_elements
        self.vertices = set(product(range(height), range(width)))

        for vertex in self.vertices:
            self.costs[vertex] = BASE_COST

        unreachable = self.terrain_elements[OBSTACLE] + self.terrain_elements[NOTHING]
        for vertex in unreachable:
            self.costs[vertex] = max(LARGE_VALUE, self.costs[vertex])
            self.vertices.remove(vertex)

        print("Remaining vertices:")
        for v in self.vertices:
            print(v)

        difficult = self.terrain_elements[DIFFICULT_TERRAIN]
        for vertex in difficult:
            self.cost[vertex] = max(BASE_COST * 2, vertex_cost)

        for goal in self.vertices:
            path_costs = self.shortest_paths(goal)
            for vertex in self.vertices:
                x, y = vertex
                neighbors = [(x - 1, y), (x - 1, y + 1), (x, y + 1), (x + 1, y), (x, y - 1)]
                neighbors = [(i, j) for (i, j) in neighbors if (i, j) in self.vertices]
                self.base_next[vertex, goal] = min(neighbors, key=lambda n:path_costs[n])
            del path_costs
            path_costs = None              

    def shortest_paths(self, point):
        path_costs = { point : 0}
        visited = set()
        queue = [point]
        while queue:
            current = queue.pop(0)
            x, y = current
            visited.add(current)
            neighbors = [(x - 1, y - 1), (x - 1, y), (x - 1, y + 1), (x, y + 1), (x + 1, y), (x + 1), (y - 1), (x, y - 1)]
            neighbors = [n for n in neighbors if n not in visited and n in self.vertices] # Ignore visited and unreachable vertices
            for n in neighbors:
                path_costs[n] = path_costs[current] + self.costs[n]
                queue.append(n)
        return path_costs

    def place(self, obstacle):
        self.deviations.add(obstacle)
        self.update_costs()

    def remove(self, obstacle):
        self.deviations.discard(obstacle)
        self.update_costs()

    def update(self):
        pass

    def path(self, vertex, goal):
        path = []
        if goal not in self.vertices:
            return path
        current = vertex
        while current != goal:
            path.append(current)
            current = self.base_next[current, goal]
        path.append(goal)
        return path

    def cost(self, path):
        return sum([self.costs[v] for v in path])