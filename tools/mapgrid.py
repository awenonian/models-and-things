"""Zoomed, gridded crops of a map image, for tracing floor plans into coordinates.

    python tools/mapgrid.py <image> <x0> <y0> <x1> <y1> <zoom> <out.png>

Crops the pixel box (x0, y0)-(x1, y1), scales it by `zoom` and draws a grid
every 10 px (stronger every 50 px, labelled), so wall positions can be read
off in image pixels. Used to trace the Reaper VIP map (projects/reaper_vip/plan.py).
Needs Pillow (pip install pillow).
"""

import sys

from PIL import Image, ImageDraw


def main(src, x0, y0, x1, y1, zoom, out):
    x0, y0, x1, y1, z = map(int, (x0, y0, x1, y1, zoom))
    im = Image.open(src).convert("RGB")
    c = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * z, (y1 - y0) * z), Image.LANCZOS)
    d = ImageDraw.Draw(c)
    for x in range(-(-x0 // 10) * 10, x1, 10):
        major = x % 50 == 0
        d.line([((x - x0) * z, 0), ((x - x0) * z, c.size[1])], fill=(255, 0, 0) if major else (255, 170, 170))
        if major:
            for yy in range(2, c.size[1], 150):
                d.text(((x - x0) * z + 2, yy), str(x), fill=(255, 0, 0))
    for y in range(-(-y0 // 10) * 10, y1, 10):
        major = y % 50 == 0
        d.line([(0, (y - y0) * z), (c.size[0], (y - y0) * z)], fill=(0, 0, 255) if major else (170, 170, 255))
        if major:
            for xx in range(2, c.size[0], 150):
                d.text((xx, (y - y0) * z + 2), str(y), fill=(0, 0, 255))
    c.save(out)


if __name__ == "__main__":
    main(*sys.argv[1:])
