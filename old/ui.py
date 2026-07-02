from collections import defaultdict

from engine_constants import WINDOW_HEIGHT, WINDOW_WIDTH
from engine_constants import LETTERS, DIGITS, LETTER_WIDTHS, LETTER_POSITIONS
from engine_constants import BREAK, menu_blue, LETTER_SCALE, ROW_HEIGHT, ROW_LENGTH, red
from engine_constants import DIALOGUE_HEIGHT, Rectangle, Sprite, count_lines, DIALOGUE_MARGIN

from batches import *

def to_red(d):
    d.shape.color = red
    return d

def to_blue(d):
    d.shape.color = menu_blue
    return d

class Text:
    def __init__(self, 
                 text, 
                 x, y,
                 scale=1,
                 max_width=False,
                 max_rows=False,
                 fixed_width=False,
                 fixed_height=False,
                 store=False,
                 batch=ui_batch,
                 fixed_position=True):
        self.entries = []
        self.entry_index = 0
        self.text = text
        self.x = x
        self.y = y
        self.dx = 0
        self.dy = 0
        self.length = 0
        self.x_shift = 0
        self.y_shift = 0
        self.max_width = int(max_width)
        self.max_rows = int(max_rows)
        self.fixed_width = int(fixed_width)
        self.fixed_height = int(fixed_height)
        self.store = store
        self.rendered_text = []
        self.letter_index = 0
        self.rows = 0
        self.store = store
        self.beeping = False
        self.time = 0
        self.scale = scale
        self.batch = batch
        self.letters = []
        self.tags = ['UI']
        
        if not max_width:
            self.max_width = sum([self.get_width(l) * LETTER_SCALE * self.scale for l in self.text])
        else:
            self.max_width = int(max_width)

        self.width = 0
        self.height = ROW_HEIGHT * LETTER_SCALE * self.scale

        self.live = True
        self.hidden = False

        self.render()

        
    def update(self, dt):

        if self.beeping:
            self.time += dt * 12
            show = cos(self.time)
            if show > 0.5:
                for letter in self.rendered_text:
                    letter.opacity = 0
            if show <= 0.5:
                for letter in self.rendered_text:
                    letter.opacity = 255

        if not self.fixed_position:        
            # Apply movement to letters
            for letter in self.letters:
                letter.x += self.dx
                letter.y += self.dy
                    
    def set_text(self, new_text):
        self.text = new_text
        self.render()
                    
    def beep(self):
        if self.beeping:
            self.beeping = False
            self.time = 0
            for letter in self.rendered_text:
                letter.opacity = 255
        else:
            self.beeping = True
        
    def dismiss(self):
        self.live = False
        self.clear()
        del self
                
    def draw_text(self, text):
        text = text.replace(' ', ' #')
        self.x_shift = 0
        self.y_shift = 0
        for word in text.split('#'):
            word_length = 10 * len(word)
            if self.x_shift + word_length >= self.max_width:
                self.x_shift = 0
                self.y_shift -= ROW_HEIGHT * LETTER_SCALE * self.scale + DIALOGUE_MARGIN
                self.height += ROW_HEIGHT * LETTER_SCALE * self.scale + DIALOGUE_MARGIN
            for letter in word:
                self.append_letter(letter)
            self.width = max(self.width, self.x_shift)

    def append_letter(self, letter):
        if letter == BREAK:
            self.x_shift = 0
            self.y_shift -= ROW_HEIGHT * LETTER_SCALE * self.scale + DIALOGUE_MARGIN
        else:
            letter_sprite, letter_width = self.get_letter_image(letter)
            self.fit_letter(letter_width)
            self.place_letter(letter_sprite, letter_width)

    # Sería fit word, para no partirlas en cualquier lado
    def fit_letter(self, width):
        if self.x_shift + width > self.length:
            self.x_shift = 0
            self.y_shift -= ROW_HEIGHT * LETTER_SCALE * self.scale + DIALOGUE_MARGIN

    def place_letter(self, letter_image, letter_width):
        letter_sprite = Sprite(letter_image,
                            self.x + self.x_shift,
                            self.y + self.y_shift,
                            batch=self.batch)
        letter_sprite.scale = LETTER_SCALE * self.scale
        self.rendered_text.append(letter_sprite)
        self.x_shift += letter_width * LETTER_SCALE * self.scale
        self.letters.append(letter_sprite)

    def clear(self):
        self.x_shift = 0
        self.y_shift = 0
        while self.rendered_text:
            letter_sprite = self.rendered_text.pop()
            letter_sprite.delete()
            del letter_sprite

    def show_next_letter(self):
        shown_last_letter = self.letter_index == len(self.rendered_letters)
        if not shown_last_letter:
            self.rendered_letters[self.letter_index].opacity = 255
            self.letter_index += 1
            
    def get_width(self, letter):
        return LETTER_WIDTHS[letter]
        
    def get_word_width(self, word):
        return sum([LETTER_WIDTHS[letter] for letter in word])

    def get_letter_image(self, letter):
        if letter in '0123456789':
            index = int(letter)
            return DIGITS[index], LETTER_WIDTHS[letter]
        else:
            index = LETTER_POSITIONS[letter]
            width = LETTER_WIDTHS[letter]
            return LETTERS[width][index], width
                
    def render(self):
        self.clear()
        self.length = sum([self.get_width(l) * LETTER_SCALE * self.scale for l in self.text])
        self.rows = count_lines(self.text, self.length)
        self.draw_text(self.text)

    def center_x(self, start, end):
        # For single-line text only
        width = sum([LETTER_WIDTHS[l] * LETTER_SCALE * self.scale  for l in self.text])
        displacement = (end - (start + width)) // 2
        self.x = start + displacement
        self.render()

    def center_y(self, start, end):
        # For single-line text only
        height = self.rows * ROW_HEIGHT
        displacement = (end - (start + height)) // 2
        self.y = start + displacement
        self.render()

    def set_position(self, x, y):
        displacement_x = x - self.rendered_text[0].x
        displacement_y = y - self.rendered_text[0].y
        for letter in self.rendered_text:
            letter.x -= displacement_x
            letter.y -= displacement_y
        self.x = x
        self.y = y

class Button:

    def __init__(self,
                 x, y,
                 width,
                 height, 
                 scale=1,
                 text=False,
                 main_press=(lambda x: False),
                 side_press=(lambda x: False),
                 out_press=(lambda x : False),
                 hover=(lambda x : False),
                 unhover=(lambda x : False),
                 shape=False,
                 store=defaultdict(lambda: []),
                 batch=ui_batch,
                 fixed_width=False,
                 fixed_height=False,
                 fixed_position=True,
                 dismiss_on_out=True,
                 persistent=False):

        self.x = x
        self.y = y
        self.dx = 0
        self.dy = 0
        self.width = width
        self.height = height
        self.main_press = main_press
        self.side_press = side_press
        self.out_press = out_press
        self.hover = hover
        self.unhover = unhover
        self.store = store
        self.beeping = False
        self.batch = batch
        self.time = 0
        self.scale = scale

        self.fixed_width = bool(fixed_width)
        self.fixed_height = bool(fixed_height)
        self.fixed_position = bool(fixed_position)
        self.dismiss_on_out = bool(dismiss_on_out)
        self.persistent = bool(persistent)

        self.live = True
        self.hidden = False

        if not shape:
            self.shape = Rectangle(self.x, self.y, self.width, self.height, menu_blue, batch=ui_background)

        if text:
            self.text = Text(text, self.x, self.y, max_width=False)
            self.width = self.text.width
            self.height = self.text.height

        self.priority = 0
        self.tags = ['UI']
        
    def update(self, dt):
        if not self.fixed_position and self.shape:
            self.shape.x += self.dx
            self.shape.y += self.dy
                    
    def set_text(self, new_text):
        if self.text:
            self.text.set_text(new_text)
        else:
            self.text = Text(new_text, self.x, self.y)
        
    def dismiss(self):
        self.live = False
        if self.shape:
            self.shape.delete()
        if self.text:
            self.text.dismiss()
        
    def collide(self, target):
        if not target:
            return False
        # Check if the character collides with the target
        x_collision = target.x <= self.x + self.x_side and self.x <= target.x + target.x_side
        y_collision = target.y <= self.y + self.y_side and self.y <= target.y + target.y_side
        return x_collision and y_collision
                
    def within(self, x, y):
        return self.x <= x and x <= self.x + self.shape.width and self.y <= y and y <= self.y + self.height

    def on_mouse_press(self, x, y, button, modifiers):
        main_click = self.within(x, y) and button == 1
        side_click = self.within(x, y) and button == 4
        clicked_out = not self.within(x, y)
        if main_click:
            self.main_press(self)
        if side_click:
            self.side_press(self)
        if clicked_out:
            self.out_press(self)

    def on_mouse_motion(self, x, y, dx, dy):
        if self.within(x, y):
            self.hover(self)
        else:
            self.unhover(self)
            
    def render(self):
        pass

    def center_x(self, start, end):
        # For single-line text only
        width = self.width
        displacement = (end - (start + width)) // 2
        self.shape.x = self.shape.x + displacement

    def set_position(self, x, y):
        self.x = x
        self.y = y
        self.shape.x = x
        self.shape.y = y
        if self.text:
            self.text.set_position(x, y)

class Menu:
    def __init__(self, x, y, options, persistent=False, centered=False):
        self.x = x
        self.y = y
        self.options = options
        self.option_buttons = []
        self.persistent = bool(persistent)
        self.height = 0
        self.width = 0
        self.centered = bool(centered)
        self.live = True

        def dismiss(button):
            return lambda x: button.dismiss()

        shift_y = 0
        for (option, call) in self.options:
            option_button = Button(self.x, self.y + int(shift_y), 10, 10, text=str(option), persistent=bool(self.persistent))
            option_button.text.render()
            shift_y += option_button.text.height
            option_button.side_press = dismiss(option_button)
            option_button.out_press = dismiss(option_button)
            def main_call(call):
                return lambda x: call(x)
            def hover(button):
                return lambda x : to_red(button)
            def unhover(button):
                return lambda x : to_blue(button)
            option_button.main_press = main_call(call)
            option_button.unhover = unhover(option_button)
            option_button.hover = hover(option_button)
            self.option_buttons.append(option_button)
            self.width = max(self.width, option_button.text.width)
            self.height += option_button.text.height
            self.option_buttons.append(option_button)

        for button in self.option_buttons:
            button.shape.width = self.width
            button.shape.height = button.text.height


        self.tags = ['UI', 'MENU']
        self.fit()

    def dismiss(self):
        self.live = False
        for button in self.option_buttons:
            button.dismiss()

    def on_mouse_press(self, x, y, button, modifiers):
        for option_button in self.option_buttons:
            option_button.on_mouse_press(x, y, button, modifiers)
        if not self.persistent:
            self.dismiss()
        return self

    def on_mouse_motion(self, x, y, dx, dy):
        for button in self.option_buttons:
            button.on_mouse_motion(x, y, dx, dy)
        return self

    def fit(self):
        x_displacement = 0
        y_displacement = 0
        if self.x + self.width > WINDOW_WIDTH:
            x_displacement = (self.x + self.width) - WINDOW_WIDTH
        if self.y + self.height > WINDOW_HEIGHT:
            y_displacement = (self.x + self.width) - WINDOW_WIDTH
        if self.x < 0:
            x_displacement = -self.x
        if self.y < 0:
            y_displacement = -self.y
        for button in self.option_buttons:
            button.set_position(button.x + x_displacement, button.y + y_displacement)