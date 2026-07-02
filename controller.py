from pyglet.window.key import Z, X, C, UP, DOWN, LEFT, RIGHT, SPACE, TAB, ENTER
from pyglet.window.key import KeyStateHandler
from pyglet.window.key import symbol_string

class Controller:

    def __init__(self, window):
        self.targets = []
        self.keyboard = KeyStateHandler()
        self.bindings = {
            Z : 'z',
            X : 'x',
            C : 'c',
            UP : 'u',
            DOWN : 'd',
            LEFT : 'l',
            RIGHT : 'r',
            SPACE : 's',
            ENTER : 'e',
            TAB : 't'
        }

    def push_target(self, target):
        self.targets.append(target)

    def pop(self):
        self.targets.pop()

    def on_key_press(self, key, modifiers):
        if key not in self.bindings:
            return
        if not self.targets:
            raise Exception('Attempted to send controller signal without any controlled entity active.')
        signal = self.bindings[key]
        press = 'press'
        self.targets[-1].send_signal(signal, press)
    
    def on_key_release(self, key, modifiers):
        if key not in self.bindings:
            return
        if not self.targets:
            raise Exception('Attempted to send controller signal without any controlled entity active.')
        signal = self.bindings[key]
        release = 'release'
        self.targets[-1].send_signal(signal, release)