"""Assembly diagram: which print tile goes where, drawn over the walls.

    python -m projects.reaper_vip.tilemap [out.png]

Writes projects/reaper_vip/images/tile_map.png by default.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

from projects.reaper_vip import plan  # noqa: E402
from projects.reaper_vip.penthouse import zones  # noqa: E402
from projects.reaper_vip.shell import floor_plan, stroke, wall_path  # noqa: E402

COLOURS = ["#f4d6a0", "#bfe3c0", "#c6d8f5", "#f5c6d0", "#e0d0f5", "#f7e3b5", "#c9eee9",
           "#f2cfb3", "#d7e8b0", "#e5c7e8", "#bfd7e0", "#f0e0c8", "#d0d0f0", "#f6d0a8"]


def main(out: str = str(Path(__file__).parent / "images" / "tile_map.png")) -> None:
    fig, ax = plt.subplots(figsize=(10, 9.2), dpi=110)
    slab = floor_plan()
    for i, (name, z) in enumerate(zones().items()):
        piece = z ^ slab
        if piece.is_empty():
            continue
        for poly in piece.to_polygons():
            ax.add_patch(Polygon(poly, closed=True, fc=COLOURS[i % len(COLOURS)], ec="#555", lw=1.2))
        x0, y0, x1, y1 = piece.bounds()
        # Label at the centroid of the biggest polygon.
        big = max(piece.decompose(), key=lambda c: c.area())
        bx0, by0, bx1, by1 = big.bounds()
        ax.text((bx0 + bx1) / 2, (by0 + by1) / 2, f"tile_{name}\n{x1 - x0:.0f} x {y1 - y0:.0f}",
                ha="center", va="center", fontsize=8, weight="bold", color="#222",
                bbox=dict(fc="white", ec="none", alpha=0.7, pad=1.5))
    for w in plan.WALLS:
        cs = stroke(wall_path(w), w.t if w.kind == "solid" else 1.6)
        for poly in cs.to_polygons():
            ax.add_patch(Polygon(poly, closed=True, fc="#333" if w.kind == "solid" else "#5b8db8", ec="none"))
    ax.set_aspect("equal")
    b = slab.bounds()
    ax.set_xlim(b[0] - 10, b[2] + 10)
    ax.set_ylim(b[1] - 10, b[3] + 10)
    ax.set_title("Reaper VIP penthouse: print tiles (mm). North is up, as on the map.")
    ax.axis("off")
    fig.tight_layout()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    print(out)


if __name__ == "__main__":
    main(*sys.argv[1:])
