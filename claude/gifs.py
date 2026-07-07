
"""
Scan a directory for sprite-sheet image files and turn them into
animated GIFs, based on their size:

* 64x64  -> extract the third 16x16 column (4 stacked tiles, one per
            row) and save it as a single animated GIF next to the
            source file.

* 64x112 -> treat the sheet as a 4-column x 7-row grid of 16x16 tiles
            and create a directory of individual GIFs:
              - rows 0-3 (one column each) become 4-frame movement
                animations: move_down, move_up, move_left, move_right
              - row 4 (single tiles) become 3-frame (duplicated)
                GIFs: attack_down, attack_up, attack_right, attack_left
              - row 5: jump_down, jump_up, jump_right, jump_left
              - row 6: downed, collect, special_a, special_b

Usage:
    python extract_column_gif.py /path/to/directory \
        [--suffix _col3] [--dir-suffix _sprites] [--duration 150] [--loop 0]
"""

import argparse
import glob
import os
from PIL import Image

TILE_SIZE = 16
GRID_SIZE = 4  # 64 / 16 (columns, and rows for the 64x64 case)
COLUMN_INDEX = 2  # 0-indexed: 0=first, 1=second, 2=third, 3=fourth

# Common image extensions to look for with glob
IMAGE_EXTENSIONS = ("*.png") # "*.jpg", "*.jpeg", "*.bmp", "*.gif", "*.tif", "*.tiff")

# 64x112 layout: movement rows (0-3), one direction per column
MOVE_NAMES = ["move_down", "move_up", "move_left", "move_right"]

# 64x112 layout: remaining rows (4, 5, 6), one name per column
ACTION_ROW_NAMES = [
    ["attack_down", "attack_up", "attack_right", "attack_left"],
    ["jump_down", "jump_up", "jump_right", "jump_left"],
    ["downed", "collect", "special_a", "special_b"],
]


def find_image_files(directory):
    """Glob for image files in the given directory, recursively."""
    files = []
    for pattern in IMAGE_EXTENSIONS:
        files.extend(glob.glob(os.path.join(directory, pattern), recursive=True))
        files.extend(glob.glob(os.path.join(directory, pattern.upper()), recursive=True))
    return sorted(set(files))


def extract_tile(img, col, row):
    """Return the 16x16 tile at the given column/row (0-indexed)."""
    x0 = col * TILE_SIZE
    y0 = row * TILE_SIZE
    return img.crop((x0, y0, x0 + TILE_SIZE, y0 + TILE_SIZE))


def extract_column_frames(img, column_index=COLUMN_INDEX, num_rows=GRID_SIZE):
    """Given a 64-wide PIL image, return a list of 16x16 frames for the
    given column index, one per row, top to bottom."""
    return [extract_tile(img, column_index, row) for row in range(num_rows)]


def save_gif(frames, out_path, duration=150, loop=0):
    """Save a list of PIL images as an animated GIF."""
    frames_rgba = [f.convert("RGBA") for f in frames]
    frames_rgba[0].save(
        out_path,
        save_all=True,
        append_images=frames_rgba[1:],
        duration=duration,
        loop=loop,
        disposal=2,
    )


def _nudge_blue_channel(img, delta):
    """Return a copy of img with every pixel's blue channel shifted by
    `delta` (clamped to 0-255). A whole-image shift like this survives
    Pillow's adaptive GIF palette quantization, unlike a single-pixel
    tweak, which tends to get quantized away on largely uniform tiles."""
    r, g, b, a = img.split()
    b = b.point(lambda v: max(0, min(255, v + delta)))
    return Image.merge("RGBA", (r, g, b, a))


def duplicate_frames(tile, count):
    """Return `count` copies of a tile, for use as GIF frames.

    Pillow's GIF encoder silently merges consecutive frames that are
    pixel-for-pixel identical (it just extends the duration of the
    previous frame instead of writing a new one). That's invisible to
    a viewer, but it means the file ends up with fewer frames than
    requested, which matters if something downstream expects an exact
    frame count. To keep a real N-frame GIF, every frame after the
    first gets its blue channel nudged by a tiny, different amount -
    imperceptible to the eye, but enough that Pillow treats each one
    as a genuinely distinct frame instead of merging it away.
    """
    frames = [tile.copy()]
    for i in range(1, count):
        frames.append(_nudge_blue_channel(tile, i))
    return frames


def process_64x64(path, img, suffix, duration, loop):
    """Extract the third 16x16 column as an animated GIF next to the file."""
    frames = extract_column_frames(img)
    base, _ext = os.path.splitext(path)
    out_path = f"{base}{suffix}.gif"
    save_gif(frames, out_path, duration, loop)
    print(f"Wrote: {out_path}")


def process_64x112(path, img, dir_suffix, duration, loop):
    """Split a 64x112 sheet into a directory of movement/action GIFs."""
    base, _ext = os.path.splitext(path)
    out_dir = f"{base}{dir_suffix}"
    os.makedirs(out_dir, exist_ok=True)

    # Rows 0-3: one column per movement direction, 4 frames each.
    for col, name in enumerate(MOVE_NAMES):
        frames = [extract_tile(img, col, row) for row in range(4)]
        out_path = os.path.join(out_dir, f"{name}.gif")
        save_gif(frames, out_path, duration, loop)
        print(f"Wrote: {out_path}")

    # Rows 4-6: single tile each, duplicated into a 3-frame GIF.
    for i, row_names in enumerate(ACTION_ROW_NAMES):
        row = 4 + i
        for col, name in enumerate(row_names):
            tile = extract_tile(img, col, row)
            frames = duplicate_frames(tile, 3)
            out_path = os.path.join(out_dir, f"{name}.gif")
            save_gif(frames, out_path, duration, loop)
            print(f"Wrote: {out_path}")


def process_directory(directory, suffix="_col3", dir_suffix="_sprites",
                       duration=150, loop=0):
    image_files = find_image_files(directory)

    if not image_files:
        print(f"No image files found in: {directory}")
        return

    processed = 0
    skipped = 0

    for path in image_files:
        try:
            with Image.open(path) as img:
                img = img.convert("RGBA")
                size = img.size

                if size == (64, 64):
                    process_64x64(path, img, suffix, duration, loop)
                    processed += 1
                elif size == (64, 112):
                    process_64x112(path, img, dir_suffix, duration, loop)
                    processed += 1
                else:
                    print(f"Skipping (not 64x64 or 64x112, is {size}): {path}")
                    skipped += 1

        except Exception as e:
            print(f"Error processing {path}: {e}")
            skipped += 1

    print(f"\nDone. Processed: {processed}, Skipped: {skipped}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Convert 64x64 or 64x112 sprite sheets into animated GIFs."
        )
    )
    parser.add_argument("directory", help="Directory containing sprite image files")
    parser.add_argument(
        "--suffix",
        default="_col3",
        help="Suffix for the 64x64 output GIF filename (default: _col3)",
    )
    parser.add_argument(
        "--dir-suffix",
        default="_sprites",
        help="Suffix for the 64x112 output directory name (default: _sprites)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=150,
        help="Duration per frame in milliseconds (default: 150)",
    )
    parser.add_argument(
        "--loop",
        type=int,
        default=0,
        help="Number of loops, 0 = infinite (default: 0)",
    )

    args = parser.parse_args()
    process_directory(
        args.directory, args.suffix, args.dir_suffix, args.duration, args.loop
    )


if __name__ == "__main__":
    main()