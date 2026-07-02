from json import dumps
from collections import defaultdict
from indices import entity_index

class Game:

    def __init__(self, initial_state):
        self.entities = set() # Deberia ser un set, porque el removal es comun
        self.index = defaultdict(lambda: set())
        self.load(initial_state)

    def add_entity(self, entity):
        entity.game = self
        self.entities.add(entity)
        for tag in entity.tags:
            self.index[tag].add(entity)

    def remove_entity(self, entity):
        self.entities.discard(entity)
        for tag in entity.tags:
            self.index[tag].discard(entity)

    def load_entity(self, data):
        constructor = entity_index[data['type']]
        return constructor(data)

    def save(self):
        entities = []
        for entity in self.entities:
            entities.append(entity.save())
        return dumps(entities)

    def load(self, data):
        for entity_data in data:
            new_entity = self.load_entity(entity_data)
            self.add_entity(new_entity)

    def update(self, dt):
        remove_next = set()
        for entity in list(self.entities):
            if entity.live:
                entity.update(dt)
            else:
                remove_next.add(entity)
        self.entities -= remove_next
        for entity in remove_next:
            entity.dismiss()