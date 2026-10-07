#!/usr/bin/env python3
"""
Pyglet Tilemap Editor  (controller + keyboard)
==============================================

Requirements:   pip install "pyglet>=2.0" pillow
Run:            python tilemap_editor.py [--width 40 --height 30 --tile-size 16 --zoom 2]

Put your tileset PNG(s) in the same directory as this script. Maps are saved as
sub-directories of this directory.

CONTROLS (PlayStation naming; SDL/Xbox equivalents in brackets)
--------------------------------------------------------------
  D-pad / Left stick  Move cursor to the adjacent tile
  X (cross) [A]       Tileset: select tile.  Tilemap: place tile (hold X and move to paint)
  Circle [B]          Tilemap: erase tile (hold and move to erase)       (extra)
  Triangle [Y]        Tilemap: pick the tile under the cursor            (extra)
  R1  or  TAB         Switch between tileset and tilemap
  L1                  Move up one layer
  L2                  Move down one layer
  R2                  Cycle through the six most recently used tiles
  Start               Open menu (Save / Save As / Load Map / Load Tileset / ...)

Keyboard equivalents: arrows, X, Z (erase), C (pick), TAB, PageUp (L1), PageDown (L2),
R (R2), ESC or M (menu/back), ENTER (Start / confirm in menus).

LOADING A TILESET
-----------------
  Menu -> Load Tileset -> choose a PNG -> use the D-pad to set the X/Y offset of the
  first tile (L1/R1 = tile size -/+1, L2/R2 = -/+8) -> press Start.

SAVE FORMAT
-----------
  <map dir>/layer_00.png, layer_01.png ...   one PNG per layer, transparent background,
                                             empty tiles are transparent
  <map dir>/meta.json                        tileset name, offset, tile size, map size
  When loading, the PNG layers are matched back to tiles of the tileset by pixel data.
"""
import argparse
import json
import os
import re
import time

import pyglet
from pyglet import shapes
from pyglet.gl import (GL_NEAREST, GL_SCISSOR_TEST, glClearColor, glDisable,
                       glEnable, glScissor)
from pyglet.math import Mat4, Vec3
from pyglet.window import key
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))

# Crisp pixel art
pyglet.image.Texture.default_min_filter = GL_NEAREST
pyglet.image.Texture.default_mag_filter = GL_NEAREST

DIRS = ('up', 'down', 'left', 'right')
DELTA = {'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1)}
KEYDIR = {key.LEFT: 'left', key.RIGHT: 'right', key.UP: 'up', key.DOWN: 'down'}
KEYACT = {key.X: 'confirm', key.Z: 'cancel', key.C: 'y', key.TAB: 'r1',
          key.PAGEUP: 'l1', key.PAGEDOWN: 'l2', key.R: 'r2',
          key.ESCAPE: 'back', key.M: 'start'}
# SDL game-controller names (pyglet) -> editor actions. PS cross == SDL 'a'.
PADBTN = {'a': 'confirm', 'b': 'cancel', 'y': 'y', 'start': 'start',
          'rightshoulder': 'r1', 'leftshoulder': 'l1',
          'dpup': 'up', 'dpdown': 'down', 'dpleft': 'left', 'dpright': 'right'}
RECENT_MAX = 6
TEXT_GRID = [list('abcdefghij'), list('klmnopqrst'), list('uvwxyz0123'),
             list('456789_-') + ['DEL', 'OK']]
BROWSER_ROWS = 15


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def pil_to_texture(img):
    img = img.convert('RGBA')
    w, h = img.size
    return pyglet.image.ImageData(w, h, 'RGBA', img.tobytes(), pitch=-w * 4).get_texture()


def label(text, x, y, size=12, color=(225, 225, 225, 255), anchor_x='left', bold=False):
    return pyglet.text.Label(text, font_size=size, x=x, y=y, anchor_x=anchor_x,
                             anchor_y='center', color=color, weight=bold)


class Outline:
    """A rectangular outline made of four thin rectangles."""

    def __init__(self, color, thickness=2):
        self.t = thickness
        self.r = [shapes.Rectangle(0, 0, 1, 1, color=color) for _ in range(4)]

    def set(self, x, y, w, h):
        t = self.t
        for rect, (rx, ry, rw, rh) in zip(self.r, ((x, y, w, t), (x, y + h - t, w, t),
                                                    (x, y, t, h), (x + w - t, y, t, h))):
            rect.x, rect.y, rect.width, rect.height = rx, ry, rw, rh

    def set_color(self, color):
        for rect in self.r:
            rect.color = color

    def draw(self):
        for rect in self.r:
            rect.draw()


class Panel:
    """A scrollable, clipped viewport."""

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.sx = self.sy = 0
        self.bg = shapes.Rectangle(x, y, w, h, color=(24, 24, 30))
        self.border = Outline((90, 90, 90, 255), 3)
        self.border.set(x - 3, y - 3, w + 6, h + 6)

    def show(self, rx, ry, rw, rh, cw, ch, m=16):
        """Scroll so the content-space rectangle (rx, ry, rw, rh) is visible."""
        if rx - m < self.sx:
            self.sx = rx - m
        if rx + rw + m > self.sx + self.w:
            self.sx = rx + rw + m - self.w
        if ry - m < self.sy:
            self.sy = ry - m
        if ry + rh + m > self.sy + self.h:
            self.sy = ry + rh + m - self.h
        self.sx = max(0, min(self.sx, cw - self.w)) if cw > self.w else 0
        self.sy = max(0, min(self.sy, ch - self.h)) if ch > self.h else ch - self.h  # top aligned


class PadHandler:
    """Receives pyglet controller events and forwards them to the editor."""

    def __init__(self, ed):
        self.ed = ed

    def on_button_press(self, controller, name):
        self.ed.pad_button(name, True)

    def on_button_release(self, controller, name):
        self.ed.pad_button(name, False)

    def on_dpad_motion(self, controller, *args):
        self.ed.pad_dpad(args)

    def on_trigger_motion(self, controller, trigger, value):
        self.ed.pad_trigger(trigger, value)

    def on_stick_motion(self, controller, stick, *args):
        if stick != 'leftstick':
            return
        if len(args) == 1:
            x, y = args[0][0], args[0][1]
        elif len(args) == 2:
            x, y = args
        else:
            return
        self.ed.pad_stick(x, y)


class Editor(pyglet.window.Window):
    def __init__(self, mw, mh, ts, zoom):
        super().__init__(1280, 720, caption='Pyglet Tilemap Editor')
        glClearColor(0.09, 0.09, 0.11, 1)
        self.zoom = zoom
        self.ts = ts
        self.ox = self.oy = 0

        # panels
        self.tp = Panel(10, 80, 420, 630)     # tileset
        self.mp = Panel(440, 80, 830, 630)    # tilemap

        # tileset state
        self.ts_name = None
        self.ts_img = None
        self.ts_sprite = None
        self.ghost = None
        self._ghost_t = None
        self.tiles_tex, self.tiles_pil, self.tile_lookup = [], [], {}
        self.cols = self.rows = 0
        self.ts_grid_shapes = []
        self.ts_grid = pyglet.graphics.Batch()

        # map state
        self.mw, self.mh = mw, mh
        self.layers = [self.blank() for _ in range(3)]
        self.layer = 0
        self.map_dir = None
        self.batch = pyglet.graphics.Batch()
        self.groups = {}
        self.sprites = {}
        self.map_bg = None
        self.map_grid_shapes = []
        self.map_grid = pyglet.graphics.Batch()

        # editing state
        self.focus = 'tileset'
        self.tcur = [0, 0]
        self.mcur = [0, 0]
        self.selected = 0
        self.recent = []
        self.slot_spr = []
        self.held = set()

        # cursors / outlines
        self.cur_out = Outline((255, 230, 60, 255))
        self.sel_out = Outline((60, 255, 120, 255))
        self.slot_bg = [shapes.Rectangle(10 + i * 44, 12, 40, 40, color=(50, 50, 60))
                        for i in range(RECENT_MAX)]

        # HUD
        self.lbl_status = label('', 300, 56)
        self.lbl_flash = label('', 300, 34, color=(255, 210, 90, 255))
        self.lbl_help = label('D-pad move | X place/select | O erase | Tri pick | R1/Tab switch | '
                              'L1/L2 layer | R2 recent | Start menu', 300, 12, 10,
                              (150, 150, 160, 255))
        self.lbl_recent = label('Recent tiles (R2)', 10, 66, 10, (150, 150, 160, 255))
        self.flash_until = 0

        # modes: edit, menu, browser, offset, text
        self.mode = 'edit'
        self.menu_items = ['Resume', 'Save', 'Save As...', 'Load Map...',
                           'Load Tileset...', 'Add Layer', 'Quit']
        self.menu_sel = 0
        self.browse = None
        self.pending = None
        self.text = None
        self.ov_batch = pyglet.graphics.Batch()
        self.ov_shapes, self.ov_labels = [], []
        self.ov_dim = shapes.Rectangle(0, 0, 1280, 720, color=(0, 0, 0, 225))

        # input state
        self.dirs_down = []
        self.pad_state = {'pad': {}, 'stick': {}}
        self.trig_state = {}
        self.pad = PadHandler(self)
        self.pads = set()
        self.cm = pyglet.input.ControllerManager()
        self.cm.push_handlers(on_connect=self._pad_connect, on_disconnect=self._pad_disconnect)
        for c in self.cm.get_controllers():
            self._pad_connect(c)

        self.build_map_visuals()
        self.follow()

        pngs = self.list_tilesets()
        if pngs:
            self.open_browser('tileset')
        else:
            self.flash('No PNG tilesets found next to the script. Put one there, then Start > Load Tileset.', 8)

    # ------------------------------------------------------------------ helpers
    @property
    def cs(self):
        """On-screen size of one tile (pixels)."""
        return self.ts * self.zoom

    def blank(self):
        return [[-1] * self.mw for _ in range(self.mh)]

    def flash(self, text, secs=4):
        self.lbl_flash.text = text
        self.flash_until = time.time() + secs

    def list_tilesets(self):
        return [f for f in sorted(os.listdir(BASE)) if f.lower().endswith('.png')]

    def list_maps(self):
        return [d for d in sorted(os.listdir(BASE))
                if os.path.isfile(os.path.join(BASE, d, 'meta.json'))]

    def group_for(self, layer):
        if layer not in self.groups:
            self.groups[layer] = pyglet.graphics.Group(order=layer)
        return self.groups[layer]

    # ------------------------------------------------------------------ controllers
    def _pad_connect(self, controller):
        if controller in self.pads:
            return
        try:
            controller.open()
            controller.push_handlers(self.pad)
            self.pads.add(controller)
            self.flash('Controller connected')
        except Exception as e:  # pragma: no cover
            print('Could not open controller:', e)

    def _pad_disconnect(self, controller):
        self.pads.discard(controller)
        self.flash('Controller disconnected')

    def _pad_dir(self, source, d, down):
        st = self.pad_state[source]
        if st.get(d, False) == down:
            return
        st[d] = down
        (self.dir_press if down else self.dir_release)(d)

    def pad_button(self, name, down):
        a = PADBTN.get(name)
        if a is None:
            return
        if a in DIRS:
            self._pad_dir('pad', a, down)
        elif down:
            self.press(a)
        else:
            self.release(a)

    def pad_dpad(self, args):
        if len(args) == 1:
            x, y = args[0][0], args[0][1]
        elif len(args) == 2:
            x, y = args
        elif len(args) == 4:
            l, r, u, d = args
            x, y = int(bool(r)) - int(bool(l)), int(bool(u)) - int(bool(d))
        else:
            return
        self._pad_dir('pad', 'left', x < -0.5)
        self._pad_dir('pad', 'right', x > 0.5)
        self._pad_dir('pad', 'up', y > 0.5)
        self._pad_dir('pad', 'down', y < -0.5)

    def pad_stick(self, x, y):
        self._pad_dir('stick', 'left', x < -0.6)
        self._pad_dir('stick', 'right', x > 0.6)
        self._pad_dir('stick', 'up', y > 0.6)
        self._pad_dir('stick', 'down', y < -0.6)

    def pad_trigger(self, trigger, value):
        name = {'lefttrigger': 'l2', 'righttrigger': 'r2'}.get(trigger)
        if not name:
            return
        was = self.trig_state.get(name, False)
        now = value > 0.5
        self.trig_state[name] = now
        if now and not was:
            self.press(name)
        elif was and not now:
            self.release(name)

    # ------------------------------------------------------------------ input plumbing
    def press(self, a):
        if a in DIRS:
            self.dir_press(a)
        else:
            self.held.add(a)
            self.act(a)

    def release(self, a):
        if a in DIRS:
            self.dir_release(a)
        else:
            self.held.discard(a)

    def dir_press(self, d):
        if d in self.dirs_down:
            return
        self.dirs_down.append(d)
        self.act(d)
        self._restart_repeat()

    def dir_release(self, d):
        if d in self.dirs_down:
            self.dirs_down.remove(d)
        self._restart_repeat()

    def _restart_repeat(self):
        pyglet.clock.unschedule(self._rep_start)
        pyglet.clock.unschedule(self._rep)
        if self.dirs_down:
            pyglet.clock.schedule_once(self._rep_start, 0.35)

    def _rep_start(self, dt):
        pyglet.clock.schedule_interval(self._rep, 0.07)

    def _rep(self, dt):
        if self.dirs_down:
            self.act(self.dirs_down[-1])

    def act(self, a):
        getattr(self, 'm_' + self.mode)(a)

    def on_key_press(self, symbol, modifiers):
        if self.mode == 'text':
            if symbol == key.BACKSPACE:
                self.text_backspace()
            elif symbol in (key.RETURN, key.ENTER):
                self.text_finish()
            elif symbol == key.ESCAPE:
                self.open_menu()
            elif symbol in KEYDIR:
                self.press(KEYDIR[symbol])
            return pyglet.event.EVENT_HANDLED
        if symbol in KEYDIR:
            self.press(KEYDIR[symbol])
        elif symbol in (key.RETURN, key.ENTER):
            self.press('confirm' if self.mode in ('menu', 'browser') else 'start')
        elif symbol in KEYACT:
            self.press(KEYACT[symbol])
        return pyglet.event.EVENT_HANDLED

    def on_key_release(self, symbol, modifiers):
        if symbol in KEYDIR:
            self.release(KEYDIR[symbol])
        elif symbol in KEYACT:
            self.release(KEYACT[symbol])
        elif symbol in (key.RETURN, key.ENTER):
            self.held.discard('confirm')
            self.held.discard('start')

    def on_text(self, text):
        if self.mode != 'text':
            return
        for ch in text:
            if ch == ' ':
                ch = '_'
            if re.fullmatch(r'[A-Za-z0-9_\-]', ch):
                self.text_add(ch)

    # ------------------------------------------------------------------ edit mode
    def m_edit(self, a):
        if a in DIRS:
            self.move_cursor(a)
        elif a == 'r1':
            self.focus = 'tilemap' if self.focus == 'tileset' else 'tileset'
        elif a == 'l1':
            self.set_layer(self.layer + 1)
        elif a == 'l2':
            self.set_layer(self.layer - 1)
        elif a == 'confirm':
            if self.focus == 'tileset':
                self.select_tile(self.tcur[1] * self.cols + self.tcur[0])
            else:
                self.place(*self.mcur)
        elif a == 'cancel' and self.focus == 'tilemap':
            self.erase(*self.mcur)
        elif a == 'y' and self.focus == 'tilemap':
            x, y = self.mcur
            t = self.layers[self.layer][y][x]
            if t >= 0:
                self.select_tile(t)
        elif a == 'r2':
            self.cycle_recent()
        elif a in ('start', 'back'):
            self.open_menu()

    def move_cursor(self, d):
        dx, dy = DELTA[d]
        if self.focus == 'tileset':
            if not self.tiles_tex:
                return
            self.tcur[0] = clamp(self.tcur[0] + dx, 0, self.cols - 1)
            self.tcur[1] = clamp(self.tcur[1] + dy, 0, self.rows - 1)
        else:
            self.mcur[0] = clamp(self.mcur[0] + dx, 0, self.mw - 1)
            self.mcur[1] = clamp(self.mcur[1] + dy, 0, self.mh - 1)
            if 'confirm' in self.held:
                self.place(*self.mcur)
            elif 'cancel' in self.held:
                self.erase(*self.mcur)
        self.follow()

    def set_layer(self, n):
        n = n % len(self.layers)
        self.layer = n
        self.refresh_opacity()
        self.flash('Layer %d / %d' % (n + 1, len(self.layers)), 2)

    def select_tile(self, t):
        if not (0 <= t < len(self.tiles_tex)):
            return
        self.selected = t
        self.touch_recent(t)

    def touch_recent(self, t):
        if t in self.recent:
            self.recent.remove(t)
        self.recent.insert(0, t)
        del self.recent[RECENT_MAX:]
        self.refresh_recent()

    def cycle_recent(self):
        if not self.recent:
            return
        i = self.recent.index(self.selected) if self.selected in self.recent else -1
        self.selected = self.recent[(i + 1) % len(self.recent)]

    def place(self, x, y):
        if not self.tiles_tex:
            self.flash('Load a tileset first (Start > Load Tileset)')
            return
        self.set_cell(self.layer, x, y, self.selected)
        if not self.recent or self.recent[0] != self.selected:
            self.touch_recent(self.selected)

    def erase(self, x, y):
        self.set_cell(self.layer, x, y, -1)

    # ------------------------------------------------------------------ map data / sprites
    def set_cell(self, l, x, y, t):
        if self.layers[l][y][x] == t:
            return
        self.layers[l][y][x] = t
        self._make_sprite(l, x, y, t)

    def _make_sprite(self, l, x, y, t):
        old = self.sprites.pop((l, x, y), None)
        if old:
            old.delete()
        if 0 <= t < len(self.tiles_tex):
            cs = self.cs
            s = pyglet.sprite.Sprite(self.tiles_tex[t], x=x * cs, y=(self.mh - 1 - y) * cs,
                                     batch=self.batch, group=self.group_for(l))
            s.scale = self.zoom
            s.opacity = 255 if l <= self.layer else 70
            self.sprites[(l, x, y)] = s

    def rebuild_sprites(self):
        for s in self.sprites.values():
            s.delete()
        self.sprites = {}
        for l, layer in enumerate(self.layers):
            for y, row in enumerate(layer):
                for x, t in enumerate(row):
                    if t >= 0:
                        self._make_sprite(l, x, y, t)

    def refresh_opacity(self):
        for (l, x, y), s in self.sprites.items():
            s.opacity = 255 if l <= self.layer else 70

    def build_map_visuals(self):
        cs, mw, mh = self.cs, self.mw, self.mh
        self.map_bg = shapes.Rectangle(0, 0, mw * cs, mh * cs, color=(36, 36, 44))
        for s in self.map_grid_shapes:
            s.delete()
        self.map_grid_shapes = []
        col = (255, 255, 255, 28)
        for i in range(mw + 1):
            self.map_grid_shapes.append(shapes.Rectangle(i * cs, 0, 1, mh * cs, color=col,
                                                         batch=self.map_grid))
        for j in range(mh + 1):
            self.map_grid_shapes.append(shapes.Rectangle(0, j * cs, mw * cs, 1, color=col,
                                                         batch=self.map_grid))

    def build_ts_grid(self):
        for s in self.ts_grid_shapes:
            s.delete()
        self.ts_grid_shapes = []
        W, H = self.ts_img.size
        z, ts, ox, oy = self.zoom, self.ts, self.ox, self.oy
        col = (255, 255, 255, 40)
        y0 = (H - oy - self.rows * ts) * z
        for c in range(self.cols + 1):
            self.ts_grid_shapes.append(shapes.Rectangle((ox + c * ts) * z, y0, 1,
                                                        self.rows * ts * z, color=col,
                                                        batch=self.ts_grid))
        for r in range(self.rows + 1):
            self.ts_grid_shapes.append(shapes.Rectangle(ox * z, (H - oy - r * ts) * z,
                                                        self.cols * ts * z, 1, color=col,
                                                        batch=self.ts_grid))

    def tile_rect(self, t):
        c, r = t % self.cols, t // self.cols
        W, H = self.ts_img.size
        z, ts = self.zoom, self.ts
        return ((self.ox + c * ts) * z, (H - self.oy - (r + 1) * ts) * z, ts * z, ts * z)

    def follow(self):
        if self.tiles_tex:
            W, H = self.ts_img.size
            x, y, w, h = self.tile_rect(self.tcur[1] * self.cols + self.tcur[0])
            self.tp.show(x, y, w, h, W * self.zoom, H * self.zoom)
        cs = self.cs
        self.mp.show(self.mcur[0] * cs, (self.mh - 1 - self.mcur[1]) * cs, cs, cs,
                     self.mw * cs, self.mh * cs)

    def refresh_recent(self):
        for s in self.slot_spr:
            s.delete()
        self.slot_spr = []
        for i, t in enumerate(self.recent):
            if t < len(self.tiles_tex):
                s = pyglet.sprite.Sprite(self.tiles_tex[t], x=12 + i * 44, y=14)
                s.scale = 36.0 / self.ts
                self.slot_spr.append(s)

    # ------------------------------------------------------------------ tileset loading
    def load_tileset(self, name, ox, oy, ts, img=None):
        if img is None:
            img = Image.open(os.path.join(BASE, name)).convert('RGBA')
        W, H = img.size
        cols, rows = (W - ox) // ts, (H - oy) // ts
        if cols < 1 or rows < 1:
            raise ValueError('Tile size / offset leave no tiles')
        tex = pil_to_texture(img)

        if self.ts_sprite:
            self.ts_sprite.delete()
        if self.ghost:
            self.ghost.delete()
        self.ts_img, self.ts_name = img, name
        self.ox, self.oy, self.ts = ox, oy, ts
        self.cols, self.rows = cols, rows
        self.ts_sprite = pyglet.sprite.Sprite(tex)
        self.ts_sprite.scale = self.zoom

        self.tiles_pil, self.tiles_tex, self.tile_lookup = [], [], {}
        for r in range(rows):
            for c in range(cols):
                x0, y0 = ox + c * ts, oy + r * ts
                tile = img.crop((x0, y0, x0 + ts, y0 + ts))
                self.tiles_pil.append(tile)
                self.tiles_tex.append(tex.get_region(x0, H - y0 - ts, ts, ts))
                if tile.getchannel('A').getbbox() is not None:
                    self.tile_lookup.setdefault(tile.tobytes(), len(self.tiles_pil) - 1)

        n = len(self.tiles_tex)
        for layer in self.layers:           # drop indices that no longer exist
            for row in layer:
                for i, t in enumerate(row):
                    if t >= n:
                        row[i] = -1

        self.selected, self.recent, self.tcur = 0, [0], [0, 0]
        self.ghost = pyglet.sprite.Sprite(self.tiles_tex[0])
        self.ghost.scale = self.zoom
        self.ghost.opacity = 150
        self._ghost_t = 0
        self.tp.sx = self.tp.sy = 0
        self.build_ts_grid()
        self.rebuild_sprites()
        self.build_map_visuals()
        self.refresh_recent()
        self.follow()
        self.flash('Tileset "%s": %d tiles (%dx%d, offset %d,%d)' % (name, n, ts, ts, ox, oy))

    # ------------------------------------------------------------------ save / load map
    def save_map(self, name):
        if not self.tiles_pil:
            self.flash('Load a tileset first')
            return
        try:
            d = os.path.join(BASE, name)
            os.makedirs(d, exist_ok=True)
            ts = self.ts
            for l, layer in enumerate(self.layers):
                img = Image.new('RGBA', (self.mw * ts, self.mh * ts), (0, 0, 0, 0))
                for y, row in enumerate(layer):
                    for x, t in enumerate(row):
                        if t >= 0:
                            img.paste(self.tiles_pil[t], (x * ts, y * ts))
                img.save(os.path.join(d, 'layer_%02d.png' % l))
            for f in os.listdir(d):                      # remove stale layers
                m = re.fullmatch(r'layer_(\d+)\.png', f)
                if m and int(m.group(1)) >= len(self.layers):
                    os.remove(os.path.join(d, f))
            with open(os.path.join(d, 'meta.json'), 'w') as fh:
                json.dump({'tileset': self.ts_name, 'offset_x': self.ox, 'offset_y': self.oy,
                           'tile_size': ts, 'width': self.mw, 'height': self.mh,
                           'layers': len(self.layers)}, fh, indent=2)
            self.map_dir = name
            self.flash('Saved %d layer(s) to "%s"' % (len(self.layers), name))
        except Exception as e:
            self.flash('Save failed: %s' % e, 8)

    def load_map(self, name):
        try:
            d = os.path.join(BASE, name)
            with open(os.path.join(d, 'meta.json')) as fh:
                meta = json.load(fh)
            self.load_tileset(meta['tileset'], meta['offset_x'], meta['offset_y'], meta['tile_size'])
            self.mw, self.mh = meta['width'], meta['height']
            ts, unmatched, layers = self.ts, 0, []
            for l in range(meta['layers']):
                grid = self.blank()
                p = os.path.join(d, 'layer_%02d.png' % l)
                if os.path.isfile(p):
                    img = Image.open(p).convert('RGBA')
                    for y in range(self.mh):
                        for x in range(self.mw):
                            tile = img.crop((x * ts, y * ts, x * ts + ts, y * ts + ts))
                            if tile.getchannel('A').getbbox() is None:
                                continue
                            t = self.tile_lookup.get(tile.tobytes())
                            if t is None:
                                unmatched += 1
                            else:
                                grid[y][x] = t
                layers.append(grid)
            self.layers = layers or [self.blank()]
            self.layer = 0
            self.mcur = [0, 0]
            self.mp.sx = self.mp.sy = 0
            self.map_dir = name
            self.rebuild_sprites()
            self.build_map_visuals()
            self.follow()
            msg = 'Loaded map "%s"' % name
            if unmatched:
                msg += ' (%d tiles did not match the tileset)' % unmatched
            self.flash(msg, 6)
        except Exception as e:
            self.flash('Load failed: %s' % e, 8)

    # ------------------------------------------------------------------ menu mode
    def open_menu(self):
        self.mode = 'menu'
        self.menu_sel = 0
        self.refresh_overlay()

    def m_menu(self, a):
        n = len(self.menu_items)
        if a == 'up':
            self.menu_sel = (self.menu_sel - 1) % n
        elif a == 'down':
            self.menu_sel = (self.menu_sel + 1) % n
        elif a == 'confirm':
            return self.menu_run(self.menu_items[self.menu_sel])
        elif a in ('cancel', 'start', 'back'):
            self.mode = 'edit'
            return
        self.refresh_overlay()

    def menu_run(self, item):
        self.mode = 'edit'
        if item == 'Save':
            if self.map_dir:
                self.save_map(self.map_dir)
            else:
                self.open_text('Save map as (directory name)', '', self.save_map)
        elif item == 'Save As...':
            self.open_text('Save map as (directory name)', self.map_dir or '', self.save_map)
        elif item == 'Load Map...':
            self.open_browser('map')
        elif item == 'Load Tileset...':
            self.open_browser('tileset')
        elif item == 'Add Layer':
            self.layers.append(self.blank())
            self.set_layer(len(self.layers) - 1)
        elif item == 'Quit':
            pyglet.app.exit()

    # ------------------------------------------------------------------ file browser mode
    def open_browser(self, kind):
        ents = self.list_tilesets() if kind == 'tileset' else self.list_maps()
        self.browse = {'kind': kind, 'ents': ents, 'sel': 0, 'top': 0}
        self.mode = 'browser'
        self.refresh_overlay()

    def m_browser(self, a):
        b = self.browse
        n = len(b['ents'])
        if a == 'up' and n:
            b['sel'] = (b['sel'] - 1) % n
        elif a == 'down' and n:
            b['sel'] = (b['sel'] + 1) % n
        elif a == 'confirm' and n:
            name = b['ents'][b['sel']]
            if b['kind'] == 'map':
                self.mode = 'edit'
                return self.load_map(name)
            return self.begin_offset(name)
        elif a in ('cancel', 'start', 'back'):
            return self.open_menu()
        if b['sel'] < b['top']:
            b['top'] = b['sel']
        if b['sel'] >= b['top'] + BROWSER_ROWS:
            b['top'] = b['sel'] - BROWSER_ROWS + 1
        self.refresh_overlay()

    # ------------------------------------------------------------------ tileset offset mode
    def begin_offset(self, name):
        try:
            img = Image.open(os.path.join(BASE, name)).convert('RGBA')
        except Exception as e:
            self.mode = 'edit'
            return self.flash('Could not open %s: %s' % (name, e), 6)
        same = name == self.ts_name
        if self.pending and self.pending.get('sprite'):
            self.pending['sprite'].delete()
        self.pending = {'name': name, 'img': img, 'sprite': pyglet.sprite.Sprite(pil_to_texture(img)),
                        'ox': self.ox if same else 0, 'oy': self.oy if same else 0, 'ts': self.ts}
        self.mode = 'offset'
        self.refresh_overlay()

    def m_offset(self, a):
        p = self.pending
        W, H = p['img'].size
        if a == 'left':
            p['ox'] -= 1
        elif a == 'right':
            p['ox'] += 1
        elif a == 'up':
            p['oy'] -= 1
        elif a == 'down':
            p['oy'] += 1
        elif a == 'l1':
            p['ts'] -= 1
        elif a == 'r1':
            p['ts'] += 1
        elif a == 'l2':
            p['ts'] -= 8
        elif a == 'r2':
            p['ts'] += 8
        elif a == 'start':
            try:
                self.load_tileset(p['name'], p['ox'], p['oy'], p['ts'], p['img'])
                self.focus = 'tileset'
            except Exception as e:
                self.flash('Tileset error: %s' % e, 6)
            p['sprite'].delete()
            self.pending = None
            self.mode = 'edit'
            return
        elif a in ('cancel', 'back'):
            p['sprite'].delete()
            self.pending = None
            return self.open_browser('tileset')
        p['ts'] = clamp(p['ts'], 2, min(W, H))
        p['ox'] = clamp(p['ox'], 0, W - p['ts'])
        p['oy'] = clamp(p['oy'], 0, H - p['ts'])
        self.refresh_overlay()

    # ------------------------------------------------------------------ text entry mode
    def open_text(self, prompt, initial, callback):
        self.text = {'prompt': prompt, 'value': initial, 'sel': [0, 0], 'cb': callback}
        self.mode = 'text'
        self.refresh_overlay()

    def text_add(self, ch):
        if len(self.text['value']) < 32:
            self.text['value'] += ch
            self.refresh_overlay()

    def text_backspace(self):
        self.text['value'] = self.text['value'][:-1]
        self.refresh_overlay()

    def text_finish(self):
        name = self.text['value'].strip()
        if not name:
            return self.flash('Enter a name first')
        cb = self.text['cb']
        self.mode = 'edit'
        cb(name)

    def m_text(self, a):
        r, c = self.text['sel']
        if a == 'left':
            c = (c - 1) % 10
        elif a == 'right':
            c = (c + 1) % 10
        elif a == 'up':
            r = (r - 1) % len(TEXT_GRID)
        elif a == 'down':
            r = (r + 1) % len(TEXT_GRID)
        elif a == 'confirm':
            k = TEXT_GRID[r][c]
            if k == 'DEL':
                self.text_backspace()
            elif k == 'OK':
                return self.text_finish()
            else:
                self.text_add(k)
        elif a == 'cancel':
            self.text_backspace()
        elif a == 'start':
            return self.text_finish()
        elif a in ('y', 'back'):
            return self.open_menu()
        self.text['sel'] = [r, c]
        self.refresh_overlay()

    # ------------------------------------------------------------------ overlay building
    def refresh_overlay(self):
        for s in self.ov_shapes:
            s.delete()
        self.ov_shapes, self.ov_labels = [], []
        W, H = self.width, self.height
        rect = lambda x, y, w, h, c: self.ov_shapes.append(
            shapes.Rectangle(x, y, w, h, color=c, batch=self.ov_batch))
        add = lambda *a, **k: self.ov_labels.append(label(*a, **k))
        hint_col = (150, 150, 160, 255)

        if self.mode == 'menu':
            add('MENU', W // 2, 640, 28, anchor_x='center', bold=True)
            for i, item in enumerate(self.menu_items):
                y = 560 - i * 46
                if i == self.menu_sel:
                    rect(W // 2 - 220, y - 19, 440, 38, (70, 90, 170, 255))
                add(item, W // 2, y, 16, anchor_x='center')
            add('D-pad: move   X: select   Circle / Start: close', W // 2, 60, 12,
                hint_col, 'center')

        elif self.mode == 'browser':
            b = self.browse
            title = 'Choose a tileset PNG' if b['kind'] == 'tileset' else 'Choose a map directory'
            add(title, W // 2, 660, 26, anchor_x='center', bold=True)
            add(BASE, W // 2, 625, 11, hint_col, 'center')
            if not b['ents']:
                add('(nothing found in this directory)', W // 2, 400, 16, anchor_x='center')
            for i in range(b['top'], min(len(b['ents']), b['top'] + BROWSER_ROWS)):
                y = 570 - (i - b['top']) * 32
                if i == b['sel']:
                    rect(W // 2 - 300, y - 14, 600, 28, (70, 90, 170, 255))
                add(b['ents'][i], W // 2 - 285, y, 14)
            add('D-pad: move   X: choose   Circle / Start: back', W // 2, 40, 12,
                hint_col, 'center')

        elif self.mode == 'offset':
            p = self.pending
            iw, ih = p['img'].size
            ts, ox, oy = p['ts'], p['ox'], p['oy']
            cols, rows = (iw - ox) // ts, (ih - oy) // ts
            add('Tileset offset: %s' % p['name'], W // 2, 690, 22, anchor_x='center', bold=True)
            add('Offset X: %d    Offset Y: %d    Tile size: %d    ->  %d x %d = %d tiles'
                % (ox, oy, ts, cols, rows, cols * rows), W // 2, 655, 15, anchor_x='center')
            add('D-pad: move offset   L1/R1: tile size -/+1   L2/R2: tile size -/+8   '
                'Start: confirm   Circle: back', W // 2, 40, 12, hint_col, 'center')
            ax, ay, aw, ah = 40, 90, 1200, 540
            s = min(aw / iw, ah / ih)
            if s >= 1:
                s = int(s)
            sp = p['sprite']
            sp.scale = s
            sp.x, sp.y = ax, ay + ah - ih * s
            by = sp.y
            if cols + rows < 700:
                col = (255, 60, 220, 190)
                for c in range(cols + 1):
                    rect(ax + (ox + c * ts) * s, by + (ih - oy - rows * ts) * s, 1, rows * ts * s, col)
                for r in range(rows + 1):
                    rect(ax + ox * s, by + (ih - oy - r * ts) * s, cols * ts * s, 1, col)

        elif self.mode == 'text':
            t = self.text
            add(t['prompt'], W // 2, 640, 24, anchor_x='center', bold=True)
            add(t['value'] + '_', W // 2, 580, 24, (255, 230, 90, 255), 'center')
            cell = 62
            x0 = W // 2 - cell * 5
            for r, row in enumerate(TEXT_GRID):
                for c, k in enumerate(row):
                    x, y = x0 + c * cell, 470 - r * cell
                    sel = [r, c] == t['sel']
                    rect(x + 3, y + 3, cell - 6, cell - 6, (70, 90, 170, 255) if sel else (45, 45, 58, 255))
                    add(k, x + cell // 2, y + cell // 2, 16 if len(k) == 1 else 12, anchor_x='center')
            add('D-pad: move   X: type   Circle: delete   Start: save   Triangle: cancel   '
                '(or just use the keyboard)', W // 2, 60, 12, hint_col, 'center')

    # ------------------------------------------------------------------ drawing
    def begin_clip(self, p):
        ratio = self.get_pixel_ratio() if hasattr(self, 'get_pixel_ratio') else 1.0
        glEnable(GL_SCISSOR_TEST)
        glScissor(int(p.x * ratio), int(p.y * ratio), int(p.w * ratio), int(p.h * ratio))
        self.view = Mat4.from_translation(Vec3(p.x - p.sx, p.y - p.sy, 0))

    def end_clip(self):
        self.view = Mat4()
        glDisable(GL_SCISSOR_TEST)

    def on_draw(self):
        self.clear()
        self.tp.bg.draw()
        self.mp.bg.draw()

        # ---- tileset panel
        self.begin_clip(self.tp)
        if self.ts_sprite:
            self.ts_sprite.draw()
            self.ts_grid.draw()
            self.sel_out.set(*self.tile_rect(self.selected))
            self.sel_out.draw()
            self.cur_out.set_color((255, 230, 60, 255) if self.focus == 'tileset'
                                   else (120, 120, 120, 255))
            self.cur_out.set(*self.tile_rect(self.tcur[1] * self.cols + self.tcur[0]))
            self.cur_out.draw()
        self.end_clip()

        # ---- tilemap panel
        self.begin_clip(self.mp)
        cs = self.cs
        self.map_bg.draw()
        self.batch.draw()
        self.map_grid.draw()
        cx, cy = self.mcur
        px, py = cx * cs, (self.mh - 1 - cy) * cs
        if self.ghost and self.focus == 'tilemap' and self.tiles_tex:
            if self._ghost_t != self.selected:
                self.ghost.image = self.tiles_tex[self.selected]
                self._ghost_t = self.selected
            self.ghost.x, self.ghost.y = px, py
            self.ghost.draw()
        self.cur_out.set_color((255, 230, 60, 255) if self.focus == 'tilemap'
                               else (120, 120, 120, 255))
        self.cur_out.set(px, py, cs, cs)
        self.cur_out.draw()
        self.end_clip()

        # ---- borders (focus highlighted)
        self.tp.border.set_color((255, 230, 60, 255) if self.focus == 'tileset' else (70, 70, 80, 255))
        self.mp.border.set_color((255, 230, 60, 255) if self.focus == 'tilemap' else (70, 70, 80, 255))
        self.tp.border.draw()
        self.mp.border.draw()

        self.draw_hud()
        if self.mode != 'edit':
            self.draw_overlay()

    def draw_hud(self):
        st = 'Layer %d/%d   Focus: %s   Cell: %d,%d   Tile: %s   Map: %s' % (
            self.layer + 1, len(self.layers), self.focus, self.mcur[0], self.mcur[1],
            self.selected if self.tiles_tex else '-', self.map_dir or '(unsaved)')
        if self.lbl_status.text != st:
            self.lbl_status.text = st
        if time.time() > self.flash_until and self.lbl_flash.text:
            self.lbl_flash.text = ''
        self.lbl_status.draw()
        self.lbl_flash.draw()
        self.lbl_help.draw()
        self.lbl_recent.draw()
        for i, bg in enumerate(self.slot_bg):
            on = i < len(self.recent) and self.recent[i] == self.selected
            bg.color = (200, 170, 40) if on else (50, 50, 60)
            bg.draw()
        for s in self.slot_spr:
            s.draw()

    def draw_overlay(self):
        self.ov_dim.draw()
        if self.mode == 'offset' and self.pending:
            self.pending['sprite'].draw()
        self.ov_batch.draw()
        for l in self.ov_labels:
            l.draw()


def main():
    ap = argparse.ArgumentParser(description='Pyglet tilemap editor')
    ap.add_argument('--width', type=int, default=40, help='map width in tiles')
    ap.add_argument('--height', type=int, default=30, help='map height in tiles')
    ap.add_argument('--tile-size', type=int, default=16, help='initial tile size in pixels')
    ap.add_argument('--zoom', type=int, default=2, help='integer display zoom')
    a = ap.parse_args()
    Editor(a.width, a.height, a.tile_size, a.zoom)
    pyglet.app.run()


if __name__ == '__main__':
    main()
