import pyglet

from geometry import *
from light import *

game_window = pyglet.window.Window(1024, 720)

figures_batch = pyglet.graphics.Batch()
shades_batch = pyglet.graphics.Batch()

@game_window.event
def on_draw():
    game_window.clear()
    figures_batch.draw()
    shades_batch.draw()

sample_obstacles = [
    Rectangle(Point(100, 200), Point(200, 300)),
    Circle(Point(300, 400), 100),
    Circle(Point(100, 100), 10),
    Rectangle(Point(500, 200), Point(600, 300))
]
'''
sample_shapes = [
    pyglet.shapes.Rectangle(100, 200, 200, 300, color=(0, 0, 255), batch=figures_batch),
    pyglet.shapes.Circle(300, 400, 100, color=(0, 255, 0), batch=figures_batch),
    pyglet.shapes.Circle(50, 100, 10, color=(0, 255, 0), batch=figures_batch),
    pyglet.shapes.Rectangle(500, 200, 600, 300, color=(0, 0, 255),batch=figures_batch)
]
'''

class Player:
    def __init__(self):
        self.shape = pyglet.shapes.Circle(0, 0, 10, color=(255, 0, 0), batch=figures_batch)
        self.position = Point(0, 0)
        self.light = Light(self.position, sample_obstacles, 1000, shades_batch)
        self.keys = {
            'up' : False,
            'left' : False,
            'right' : False,
            'down' : False
        }

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.UP:
            self.keys['up'] = True
        elif symbol == pyglet.window.key.LEFT:
            self.keys['left'] = True
        elif symbol == pyglet.window.key.RIGHT:
            self.keys['right'] = True
        elif symbol == pyglet.window.key.DOWN:
            self.keys['down'] = True

    def on_key_release(self, symbol, modifiers):
        if symbol == pyglet.window.key.UP:
            self.keys['up'] = False
        elif symbol == pyglet.window.key.LEFT:
            self.keys['left'] = False
        elif symbol == pyglet.window.key.RIGHT:
            self.keys['right'] = False
        elif symbol == pyglet.window.key.DOWN:
            self.keys['down'] = False

player = Player()

pyglet.gl.glClearColor(1.0, 1.0, 1.0, 1.0)

game_window.push_handlers(player)

def update(dt):
    speed = 300
    if player.keys['left']:
        player.position.x -= speed * dt
    if player.keys['up']:
        player.position.y += speed * dt
    if player.keys['down']:
        player.position.y -= speed * dt
    if player.keys['right']:
        player.position.x += speed * dt
    player.shape.y = player.position.y
    player.shape.x = player.position.x
    player.light.update(dt)

pyglet.clock.schedule_interval(update, 1/60.0)

if __name__ == '__main__':
    pyglet.app.run()