from collections import defaultdict
from random import choice as random_element

from ui import Text, Button, Menu
from pyglet.shapes import Rectangle
from pyglet.sprite import Sprite
from pyglet.resource import image

from engine_constants import WINDOW_HEIGHT, LETTER_SCALE, ROW_HEIGHT, WINDOW_WIDTH, PORTRAIT_BAR_WIDTH, MARGIN, DIALOGUE_BAR_WIDTH
from engine_constants import menu_blue, ui_batch, over_ui_batch, highlight_red, highlight, unhighlight, ui_background
from engine_constants import ALTERNATIVES, SEQUENCE, CHOICE

from facts import facts

CLOSEUP_WIDTH = 45
CLOSEUP_SCALE = 3
CLOSEUP_MARGIN = 5
CLOSEUP_SHIFT = CLOSEUP_WIDTH * CLOSEUP_SCALE + CLOSEUP_MARGIN

MARGIN_SIZE = 5

BAR_HEIGHT = 4 * LETTER_SCALE * ROW_HEIGHT + MARGIN_SIZE * LETTER_SCALE
BAR_LENGTH = WINDOW_WIDTH - PORTRAIT_BAR_WIDTH
LOW_X = PORTRAIT_BAR_WIDTH
LOW_Y = 0
HIGH = WINDOW_HEIGHT - BAR_HEIGHT 

MAX_LINE_WIDTH = WINDOW_WIDTH - CLOSEUP_SHIFT - PORTRAIT_BAR_WIDTH - MARGIN

# Filter by facts

class Dialogue:

    def check_conditions(line):

        if ":if" not in line and ":then" not in line:
            return True

        if ":if" in line and ":then" not in line:
            parts = line.split(":if")
            if len(parts) != 2:
                print("Conditional does not split the line in only two distinct parts")
                print(line)
                return False
            if len(parts[1].split(",")) == 0:
                print("Conditional does not have recognizable conditions")
                print(line)
                return False
            return True

        if ":then" in line and ":if" not in line:
            parts = line.split(":then")
            if len(parts) != 2:
                print("Consequential does not split the line in only two distinct parts")
                print(line)
                return False
            if len(parts[1].split(",")) == 0:
                print("Consequential does not have recognizable conditions")
                print(line)
                return False
            return True

        if ":then" in line and ":if" in line:
            line = line.replace(":then", ":::then").replace(":if", ":::if")
            parts = line.split(":::")
            if len(parts) != 3:
                print("Line with both conditions and consequences is not well formed")
                print(line)
                return False
            begin, first, second = parts
            if not (first.startsWith("then") and second.startsWith("if") or first.startsWith("if") and second.startsWith("then")):
                print("Order of conditionals and/or consequentials is incorrect")
                print(line)
                return False

        return True

    def check_wellformedness(lines):
        is_string = isinstance(lines, str)
        is_list = isinstance(lines, list)
        if is_string:
            return Dialogue.check_conditions(lines)
        if is_list:
            if len(lines) < 2:
                print('Found a line with less than two elements:')
                for line in lines:
                    print(line)
                print()
                return False
            is_headed = lines[0].startsWith(ALTERNATIVES) or lines[0].startsWith(SEQUENCE) or lines[0].startsWith(CHOICE)
            if not is_headed:
                print('Found a line without a well-formed head')
                for line in lines:
                    print(line)
                print()
                return False
            if not Dialogue.check_conditions(lines[0]):
                print("Found a line whose head has ill-formed conditions or consequences")
                print(lines[0])
                return False
            is_well_tailed = all([Dialogue.check_wellformedness(line) for line in lines[1:]])
            return is_well_tailed

    def __init__(self, entries):

        self.entries = entries
        self.current_label = False # Write only, used for testing
        self.current_text = False # Write only, used for testing
        self.current = False
        self.choosing = False
        self.choices = []
        self.x_side = BAR_LENGTH
        self.y_side = BAR_HEIGHT
        self.store = defaultdict(lambda : [])
        self.shape = Rectangle(0, 0, BAR_LENGTH, BAR_HEIGHT, color=menu_blue, batch=ui_background)
        self.closeup = ''
        self.stack = []
        self.index = 0
        self.pop_entry()
        self.normal_entry = False
        self.persistent = True
        self.live = True

        if not entries:
            self.dismiss()

    def dismiss(self):
        if self:
            if self.current:
                self.current.dismiss()
            if self.shape:
                self.shape.delete()
                del self.shape
            if self.closeup:
                del self.closeup
            self.persistent = False
            self.live = False

    def pop_entry(self):

        # Clear dependent UI elements 'before putting on the new ones'
        if self.current:
            self.current.dismiss()
        if self.choices:
            self.choices.dismiss()
            self.choices = False

        # Display the next entry
        if self.entries:

            # First, look for the current dialogue tree node

            entry = self.entries
            for index in self.stack:
                if index < len(entry):
                    entry = entry[index]
            assert isinstance(entry, list)

            # See which type of node it is

            entry_label = self.entry_label(entry)
            is_sequence = SEQUENCE in entry_label
            is_alternative = ALTERNATIVES in entry_label
            is_choice = CHOICE in entry_label

            # Filter out unavailable options
            available_indices = self.filter(entry)
            max_index = max(available_indices)

            # Get the next available index
            while self.index not in available_indices and self.index <= max_index:
                self.index += 1

            # Next follow lots of disjoint cases with early return (sorry):

            # If you finished the current entry (which happens iff the current index 
            # is greater than the largest available index) and there is nothing on the stack, dismiss
            if self.index > max_index and not self.stack:
                self.dismiss()
                return
            
            # If you've finished the current entry, and there is something on the stack, pop the stack,
            # to 'go up one level' in the dialogue tree
            if self.index > max_index and self.stack:
                self.index = self.stack.pop(-1) + 1
                self.pop_entry()
                return

            # If the current entry is a sequence, and it's not finished, display the next entry
            if is_sequence and self.index <= max_index:
                # If the next entry is text, show it
                if isinstance(entry[self.index], str):
                    current_index = int(self.index)
                    self.choosing = False
                    self.index += 1
                    self.current = self.common_entry(entry[current_index])
                    return
                    
                # If the next entry is nested, push to the stack and pop again
                if isinstance(entry[self.index], list):
                    self.stack.append(self.index)
                    self.index = 0
                    self.pop_entry()
                    return

            # If the current entry is an alternative, you have to either choose a random alternative
            # and stay there (if the alternative is not a leaf), or display a leaf, and immediately
            # go back, but not to the alternative node, but the one immediately after it.
            if is_alternative:
                alternative_index = random_element(list(available_indices)) # From 1 on, because the first one is always 'ALTERNATIVE'
                entry = entry[alternative_index]

                if isinstance(entry, str):
                    self.choosing = False
                    self.index = self.stack.pop(-1) + 1
                    self.current = self.common_entry(entry[current_index])
                    return

                if isinstance(entry, list):
                    self.stack.append(self.index) # So that after finishing with the selected entry and popping from the stack one continues from where the alternative left
                    self.index = 1
                    self.pop_entry()
                    return

            # Choices are not supposed to contain branches (just each of the available dialogue options),
            # So no need to handle the leaves-vs-non leaves cases.
            # The case where the list of dialogue options is empty is not handled. That is a bug.
            if is_choice:
                self.choosing = True
                self.index += 1
                self.current = self.choice_entry(entry)
                # But how do we not end up in the same place after popping?
                # We assume choices are never inside alternatives, and always
                # Inside sequences
                return

        assert False

    def consequences(self, entry):
        # Obtain the conditions that will hold after choosing a dialogue option

        # TODO: Let sequence options and alternative options add facts too, 
        # so that you don't have to add them manually using some other mechanisms,
        # when it would make sense for something to be true just after sb. said it
        # (e.g. 'Chara asked you to visit Place', 'You now know who Chara is', 
        # 'You overheard Captain McPlotter's plot') 
        assert isinstance(entry, str)
        if ":then" in entry:
            entry, consequences = entry.split(":then")
            consequences = [c.strip() for c in consequences.split(",")]
            consequences = list(consequences)
        else:
            consequences = []
        return consequences
    
    def conditions(self, entry):
        # Obtain preconditions for a dialogue option

        assert isinstance(entry, str)
        if ":if" in entry:
            entry, conditions = entry.split(":if")
            conditions = [c.strip() for c in conditions.split(",")]
            conditions = list(conditions)
        else:
            conditions = []
        return conditions
    
    def get_text(self, entry):
        # Obtain 'just the text' from a leaf entry
        if ':then' in entry:
            entry, _ = entry.split(':then')
        if ':if' in entry:
            entry, _ = entry.split(':if')
        return entry.strip()
    
    def check_entry(self, entry):
        # Decide if an entry must be shown or not given the current facts

        if isinstance(entry, list):
            conditions = self.conditions(entry[0])
        if isinstance(entry, str):
            conditions = self.conditions(entry)
        return facts.check(conditions)
    
    def filter(self, entry):
        # Output a list with the indices of the 'available' entries within an entry, given the current facts
        if isinstance(entry, list):
            return set(t[0] + 1 for t in enumerate(entry[1:]) if self.check_entry(t[1]))
        if isinstance(entry, str):
            raise Exception('Tried to filter entries from a leaf entry')

    def entry_label(self, entry):
        # Obtain a label from an entry, or raise an error if the entry is a leaf

        if isinstance(entry, list):
            label = self.get_text(entry[0])
            return label
        else:
            raise Exception("Tried to get a label from a leaf entry")
    
    def read_entry(self, entry):

        # For nodes
        if isinstance(entry, list):
            parts = entry[1:]
            head = entry[0]

        # For leaves
        if isinstance(entry, str):
            head = entry
            parts = []

        # Check if the head has a portrait label
        if '[' in head:
            close_index = entry.find(']')
            head = head[close_index + 1:]
            portrait_name = entry[1:close_index]

        else:
            portrait_name = False
        
        # Return
        return head, parts, portrait_name

    def common_entry(self, entry):
        self.normal_entry = True
        consequences = self.consequences(entry)
        text = self.get_text(entry)
        text, _, portrait_text = self.read_entry(text)

        for consequence in consequences:
            facts.add_fact(consequence)
        shift_y = 3 * ROW_HEIGHT * LETTER_SCALE
        if not portrait_text:
            entry_text = Text(text, MARGIN, shift_y, max_width=DIALOGUE_BAR_WIDTH, max_rows=4, fixed_position=True)
        if portrait_text:
            entry_text = Text(text, CLOSEUP_SHIFT, shift_y, max_width=(DIALOGUE_BAR_WIDTH - CLOSEUP_SHIFT), max_rows=4, fixed_position=True)
            closeup_path = f'sprites/DIALOGUE/{portrait_text}.png'
            self.closeup = Sprite(image(closeup_path), 0, 0, batch=over_ui_batch)
            self.closeup.scale = CLOSEUP_SCALE
        self.shape.height = 4 * ROW_HEIGHT * LETTER_SCALE + MARGIN_SIZE * LETTER_SCALE
        self.shape.width = WINDOW_WIDTH - PORTRAIT_BAR_WIDTH
        return entry_text
    
    def choice_entry(self, entry):
        # Note all valid choice dialogue entries must have at least two different choices, and one text only entry.
        # Otherwise, indexing assumptions lead to popping out of an empty stack, or advancing an incorrect number of steps
        # in dialogue.
        self.normal_entry = False
        entry = entry[1:] # Remove the 'CHOICE' head
        text, choices, portrait_text = self.read_entry(entry)
        text = self.get_text(text)
        shift_y = len(choices) * ROW_HEIGHT * LETTER_SCALE
        counter = 1
        initial_x = MARGIN
        bar_width = int(BAR_LENGTH)
        if portrait_text or self.closeup:
            initial_x = CLOSEUP_SHIFT
            bar_width = MAX_LINE_WIDTH
        pair_choices = []
        for index, choice in enumerate(choices):
            conditions = self.conditions(choice)
            consequences = self.consequences(choice)
            choice_text = self.get_text(choice)
            # If self.game.facts.check(conditions):
            def choice_callback(text, cons):
                return lambda x: self.choose((f"[{index+1}] " + text, cons))
            pair_choices.append((choice_text, choice_callback(choice_text, consequences)))
        options_y = (len(pair_choices) - 1) * ROW_HEIGHT
        self.choices = Menu(initial_x, options_y, pair_choices, persistent=True)
        self.choices.persistent = True
        for button in self.choices.option_buttons:
            button.persistent = True
        self.choices.fit()
        self.store['CONTROLLER'].add(self.choices)
        choice_entry_y = 3 * ROW_HEIGHT * LETTER_SCALE
        if self.choices.height > choice_entry_y:
            choice_entry_y = self.choices.height
        choice_entry = Text(text, initial_x, choice_entry_y, max_width=MAX_LINE_WIDTH, fixed_position=True)
        choice_entry.priority = 4
        self.shape.height = choice_entry_y + ROW_HEIGHT * LETTER_SCALE + MARGIN_SIZE * LETTER_SCALE
        self.shape.width = WINDOW_WIDTH - PORTRAIT_BAR_WIDTH
        return choice_entry

    def choose(self, choice):
        # Run the code in charge of 'executing' a chosen dialogue option
        choice, consequences = choice
        print('Chosen: ', choice)
        for consequence in consequences:
            facts.add_fact(consequence)
        if self.stack:
            self.index = self.stack.pop(-1) + 1
            self.pop_entry()

    def skip(self):
        # Get the next entry (the interface which you would make visible if there where private and public methods)
        self.pop_entry()

    def on_mouse_press(self, x, y, button, modifiers):
        if x <= self.shape.width and y <= self.shape.height and not self.choices:
            self.pop_entry()

    def on_mouse_motion(self, x, y, dx, dy):
        pass

