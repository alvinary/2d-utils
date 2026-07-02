from pyglet.sprite import Sprite
from utils import animation_from_gif
from batches import occlusion_batch
from tags import PARTICLE

class Particle:

    def __init__(self, x, y, animation, lifetime):
        self.x = x
        self.y = y
        self.animation = animation_from_gif('vfx/' + animation + '.gif')
        self.lifetime = lifetime
        self.shape = Sprite(self.animation,
                            self.x - 8 * 3,
                            self.y - 8 * 3,
                            batch=occlusion_batch)
        self.shape.x -= self.shape.width // 2
        self.shape.y -= self.shape.width // 2
        self.shape.scale = 3
        self.tags = [PARTICLE]
        self.live = True

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime < 0:
            self.dismiss()
        
    def dismiss(self):
        self.shape.opacity = 0
        self.live = False