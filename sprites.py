from batches import main_batch
from pyglet.sprite import Sprite as PygletSprite
from constants import SPRITE_SCALING

from batches import main_batch

from pyglet.resource import animation as load_animation
from pyglet.sprite import Sprite as PygletSprite

from constants import SPRITE_SCALING

def load_phase(sprite_set, phase):
    animation_path = f"sprites/{sprite_set}/{phase}.gif"
    return load_animation(animation_path)

class Sprite:

    def __init__(self, x, y, sprite_set, deafult_phase='stand', phases=['stand']):
        self.phase = deafult_phase
        self.phase_set = phases
        self.next_phase = False
        self.phase_sequence = []
        self.playing_sequence = False
        self.animation_timer = 1.0
        self.animations = {}
        for phase in self.phase_set:
            self.animations[phase] = load_phase(sprite_set, phase)
        assert self.animations[self.phase]
        self.shape = PygletSprite(self.animations[self.phase],
                                  x,
                                  y,
                                  batch=main_batch)
        self.shape.scale = SPRITE_SCALING

    def update(self, dt):
        if self.animation_timer >= 0:
            self.animation_timer -= dt
        if self.animation_timer < 0 and self.playing_sequence and self.phase_sequence:
            phase = self.phase_sequence.pop(0)
            self.animation_timer = 1.0
            self.set_animation(phase)
        elif self.animation_timer < 0 and self.playing_sequence and not self.phase_sequence:
            self.playing_sequence = False

    def set_animation(self, phase):
        self.phase = phase
        if self.shape.image != self.animations[phase]:
            self.shape.image = self.animations[phase]

    def play_once(self, once, then_to):
        self.set_animation(once)
        self.next_animation = then_to
        self.animation_timer = self.animations[once].get_duration()

    def set_sequence(self, sequence):
        self.playing_sequence = True
        self.animation_sequence = list(sequence)
        self.animation_sequence.append(self.animation)

    def dismiss(self):
        self.live = False
        del self.shape
        self.shape = None