#!/usr/bin/env python3
"""
split_to_gif.py

Splits an image evenly into a given number of vertical frames (slices)
and writes them out as an animated GIF.

Usage:
    python split_to_gif.py input.png 8
    python split_to_gif.py input.png 8 -o output.gif -d 150
"""

import argparse
import os
import sys

from PIL import Image


def parse_args():
    parser = argparse.ArgumentParser(
        description="Split an image into N evenly-sized frames and save as an animated GIF."
    )
    parser.add_argument(
        "image_path",
        type=str,
        help="Path to the input image file.",
    )
    parser.add_argument(
        "num_frames",
        type=int,
        help="Number of frames to split the image into.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output GIF file name. Defaults to the input file name with a .gif extension.",
    )
    parser.add_argument(
        "-d", "--duration",
        type=int,
        default=100,
        help="Duration of each frame in milliseconds (default: 100).",
    )
    return parser.parse_args()


def split_image_into_frames(image, num_frames):
    """Split an image into `num_frames` vertical slices, evenly, regardless of width.

    Handles widths that don't divide evenly by distributing the remainder
    pixels across the first few slices (each of those gets one extra pixel),
    so all slices are covered and no pixel columns are skipped or duplicated.
    """
    width, height = image.size

    if num_frames < 1:
        raise ValueError("num_frames must be at least 1")
    if num_frames > width:
        raise ValueError(
            f"num_frames ({num_frames}) cannot exceed the image width ({width}px)"
        )

    base_slice_width = width // num_frames
    remainder = width % num_frames

    frames = []
    x = 0
    for i in range(num_frames):
        slice_width = base_slice_width + (1 if i < remainder else 0)
        box = (x, 0, x + slice_width, height)
        frame = image.crop(box)
        frames.append(frame)
        x += slice_width

    return frames


def main():
    args = parse_args()

    if not os.path.isfile(args.image_path):
        print(f"Error: input file not found: {args.image_path}", file=sys.stderr)
        sys.exit(1)

    try:
        image = Image.open(args.image_path)
        image.load()
    except Exception as exc:
        print(f"Error: could not open image: {exc}", file=sys.stderr)
        sys.exit(1)

    # Normalize mode so GIF saving/palette conversion behaves consistently.
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")

    try:
        frames = split_image_into_frames(image, args.num_frames)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = args.output
    else:
        base, _ext = os.path.splitext(args.image_path)
        output_path = base + ".gif"

    save_kwargs = dict(
        save_all=True,
        append_images=frames[1:],
        duration=args.duration,
        loop=0,
    )

    if image.mode == "RGBA":
        # Preserve transparency where possible.
        save_kwargs["disposal"] = 2

    frames[0].save(output_path, **save_kwargs)

    print(f"Wrote {len(frames)} frame(s) to '{output_path}' "
          f"({args.duration} ms/frame).")


if __name__ == "__main__":
    main()
