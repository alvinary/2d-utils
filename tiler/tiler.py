from PIL import Image

from itertools import product

# TODO: omit transparent / absent tiles
# TODO: replace shapes until fixpoint or cap is reached
# TODO: add object layers (layers that output a json with a list of entities instead of a map png)

class Tiler:
    def __init__(self, tile_map, tile_size, shapes_map):
        self.tile_map = tile_map
        self.tile_size = tile_size
        self.shapes_map = shapes_map

    def match_shape(self, tiles, shape):
        # Translate the shape to the origin
        # If there is a match (intersections equal), return the translated coordinates and their contents
        tiles_set = set([((x, y, tiles[x, y]) for x, y in tiles.keys())])
        matches = []
        for (x, y) in tiles.keys():
            translated_shape = self.translated_shape(shape, x, y)
            translated_shape_set = set([((x, y, translated_shape[x, y]) for x, y in translated_shape.keys())])
            if translated_shape_set <= tiles_set:
                matches.append(translated_shape)
        return matches

    def translated_shape(self, shape, x, y):
        new_shape = {}
        min_x = min([x for x, y in shape.keys()])
        min_y = min([y for x, y in shape.keys()])
        delta_x = x - min_x
        delta_y = y - min_y
        for (x, y) in shape.keys():
            new_shape[x + delta_x, y + delta_y] = shape[x, y]
        return new_shape

    def replace(self, layer, source, target):
        for pixel in source:
            layer.pop(pixel)
        for pixel in target:
            layer[pixel] = target[pixel]
        return layer

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
            sorted_shapes = list(reversed(sorted(self.shapes_map.keys(), key=(lambda x: len(x.keys())))))
            for shape in sorted_shapes:
                self.replace_all(layer_tiles, shape, self.shape_map[shape])
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

if __name__ == '__main___':
    sample_map = {
        (255, 0, 0) : 'tiles/rock.png',
        (0, 0, 255) : 'tiles/water.png',
        (0, 255, 0) : 'tiles/sand.png'
    }
    tyler = Tiler(sample_map, 16, {})
    tyler.save_map_pngs('mapapa', ['layer.png'])