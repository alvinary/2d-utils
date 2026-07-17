from PIL import Image

from itertools import product

# TODO:
# Omit tiles without a match
# Report tiles without a match
# Read mapping from file
# Report duplicate keys (with different or the same values)
# Report duplicate values (with the same or different keys)

class TilemapTagger:

    # Copy-paste of InverseTiler, but for annotations

    def __init__(self, annotations_map, source_size):
        self.annotations_map = annotations_map
        self.source_size = source_size

    def normalize(self, image, i, j, window=False):
        image_pixels = image.load()
        if window:
            window_size = int(window)
        else:
            window_size = int(self.source_size)
        new = set()
        for x, y in product(range(i, i + window_size), range(j, j + window_size)):
            new.add((x - i, y - j, image_pixels[x, y]))
        return frozenset(new)

    def annotations(self, source_image):
        block_width = source_image.width // self.source_size
        block_height = source_image.height // self.source_size
        target_width = block_width * self.target_size
        target_height = block_height * self.target_size
        map_annotation = []
        for i, j in product(range(block_width), range(block_height)):
            source_tile = self.normalize(source_image, i * self.source_size, j * self.source_size)
            annotation = (i, j, self.annotation_map[source_tile])
        return map_annotation

class InverseTiler:

    def __init__(self, tile_map, source_size, target_size):
        self.tile_map = tile_map
        self.source_size = source_size
        self.target_size = target_size

    def normalize(self, image, i, j, window=False):
        image_pixels = image.load()
        if window:
            window_size = int(window)
        else:
            window_size = int(self.source_size)
        new = set()
        for x, y in product(range(i, i + window_size), range(j, j + window_size)):
            new.add((x - i, y - j, image_pixels[x, y]))
        return frozenset(new)

    def reverse_map(self, source_image):
        # TODO: Handle errors / at least warn users when the tile size does not
        # cover the source image evenly
        block_width = source_image.width // self.source_size
        block_height = source_image.height // self.source_size
        target_width = block_width * self.target_size
        target_height = block_height * self.target_size
        reversed_tilemap = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
        for i, j in product(range(block_width), range(block_height)):
            source_tile = self.normalize(source_image, i * self.source_size, j * self.source_size)
            target_tile = self.tile_map[source_tile]
            reversed_tilemap.paste(target_tile, (i * self.target_size, j * self.target_size))
        return reversed_tilemap


class Tiler:
    def __init__(self, tile_map, tile_size):
        self.tile_map = tile_map
        self.tile_size = tile_size

    # Sería mejor que fueran las imagenes, no los paths
    def make_map(self, name, layer_paths):
        output_layers = []
        for layer_path in layer_paths:
            layer_image = Image.open(layer_path)
            layer_pixels = layer_image.load()
            layer_tiles = {}
            width = layer_image.width
            height = layer_image.height
            for i, j in product(range(width), range(height)):
                tile_color = layer_pixels[i, j]
                if tile_color in self.tile_map.keys():
                    layer_tiles[i, j] = self.tile_map[tile_color]
                else:
                    distance = lambda x : sum([abs(tile_color[i]**2 - x[i]**2) for i in [0, 1, 2]])
                    colors = self.tile_map.keys()
                    tile_color = min(colors, key=distance)
                    layer_tiles[i, j] = self.tile_map[tile_color]
            output_layers.append(layer_tiles)
        return output_layers

    def make_map_pngs(self, name, layer_paths):
        return list([self.tiles_to_png(layer) for layer in self.make_map(name, layer_paths)])

    def save_map_pngs(self, name, layer_paths):
        for index, image in enumerate(self.make_map_pngs(name, layer_paths)):
            image.save(name + "_" + str(index) + ".png")

    def tiles_to_png(self, tiles_dict):
        tiles_shift_x = 0
        tiles_shift_y = 0
        all_x = list([x for x, y in tiles_dict.keys()])
        all_y = list([y for x, y in tiles_dict.keys()])
        width = (max(all_x) + -min(all_x) + 1) * self.tile_size
        height = (max(all_y) + -min(all_y) + 1)  * self.tile_size
        layer_png = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        tiles_sources = {}
        for (x, y) in tiles_dict.keys():
            tile_name = tiles_dict[x, y]
            if tile_name in tiles_sources:
                tile_image = tiles_sources[tile_name]
            else:
                tile_image = Image.open(tile_name)
                tiles_sources[tile_name] = tile_image
            layer_png.paste(tile_image, (x * self.tile_size, y * self.tile_size))
        return layer_png


sample_map = {
    (255, 0, 0) : 'tiles/rock.png',
    (0, 0, 255) : 'tiles/water.png',
    (0, 255, 0) : 'tiles/sand.png'
}

sample_replacements = {}

tyler = Tiler(sample_map, 16)
tyler.save_map_pngs('mapapa', ['layer.png'])

colors = [(0, 255, 0), (0, 0, 255), (255, 0, 0)]
paths = ['tiles/sand.png', 'tiles/water.png', 'tiles/rock.png']
images = [Image.open(p) for p in paths]
inverse = InverseTiler({}, 16, 1)
reverse_map = {}
for index, image in enumerate(images):
    assert(inverse.normalize(image, 0, 0) == inverse.normalize(image, 0, 0))
    inverse.tile_map[inverse.normalize(image, 0, 0)] = Image.new("RGBA", (1, 1), tuple(list(colors[index]) + [255]))
assert inverse.normalize(Image.open('mapapa_0.png'), 0, 0) == inverse.normalize(Image.open('tiles/rock.png'), 0, 0)
reversed_tilemap = inverse.reverse_map(Image.open('mapapa_0.png'))
reversed_tilemap.save('revu_revu.png')