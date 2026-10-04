"""Reaper VIP -- Steel Jackhammer's penthouse (Cy_Borg starter adventure).

The whole flat as cutaway floor tiles: low walls, furniture and fittings from
the map's notes, and a corridor with the lift and stairs where the guards
stand. See README.md.

Run from the repo root:
    python -m projects.reaper_vip.penthouse

Outputs (in projects/reaper_vip/output/):
    penthouse_assembled.stl   the whole flat as it sits on the table (preview)
    print/*.stl               the print tiles and loose parts, already oriented
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from manifold3d import CrossSection, JoinType, Manifold, OpType

from modelkit.csg import box, extrude_xy, section, union
from modelkit.export import export_parts
from projects.reaper_vip import details, plan
from projects.reaper_vip.plan import M
from projects.reaper_vip.shell import FLOOR_T, TOP, build_shell, smooth

OUT_DIR = Path(__file__).parent / "output"
UP = (0.0, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Print tiles
# ---------------------------------------------------------------------------


def _rect(x0, y0, x1, y1) -> CrossSection:
    return section([M(x0, y0), M(x1, y0), M(x1, y1), M(x0, y1)])


def _holo_zone() -> CrossSection:
    (ax, ay), (bx, by) = plan.HOLO_DIAG
    d = np.array([bx - ax, by - ay], float)
    d /= np.linalg.norm(d)
    n_sw = np.array([-d[1], d[0]])          # map coords: points south-west
    if n_sw[0] > 0:
        n_sw = -n_sw
    t = next(w.t for w in plan.WALLS if w.name == "holo_diag")
    a = np.array([ax, ay]) + n_sw * t / 2 - d * 500
    b = np.array([bx, by]) + n_sw * t / 2 + d * 500
    half = section([M(*a), M(*b), M(*(b - n_sw * 1000)), M(*(a - n_sw * 1000))])
    return half ^ _rect(605.5, 457.5, plan.BIG, plan.BIG)


def _dining_zone() -> CrossSection:
    t = next(w.t for w in plan.WALLS if w.name == "dining_glass")
    pts = smooth(plan.DINING_CURVE) + [(300, 702), (300, 400), (700, 400), (700, 600)]
    inside = section([M(*q) for q in pts]).offset(t / 2 + 0.4, JoinType.Miter, 2.0)
    return inside ^ _rect(405.0, 486.5, 605.5, plan.BIG)


def zones() -> dict[str, CrossSection]:
    out: dict[str, CrossSection] = {}
    taken = CrossSection()
    for name, spec in plan.ZONES:
        if spec == "holo":
            z = _holo_zone()
        elif spec == "dining":
            z = _dining_zone()
        else:
            z = CrossSection.batch_boolean([_rect(*r) for r in spec], OpType.Add)
        z -= taken
        out[name] = z
        taken += z
    return out


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


MIN_WALL = 1.2      # anything thinner than this along a seam is a sliver
SEAM_BAND = 2.0     # how far from a seam to look for slivers
SEAM_GAP = 0.01     # each tile edge is pulled in this far


def _slivers(flat: Manifold, zs: dict[str, CrossSection]) -> dict[str, CrossSection]:
    """Hand thin slivers back to the tile they belong with.

    A seam on a wall face also shaves off whatever stands proud of that face
    (door-frame lips, the corners of mullions on a curve, wall end caps), leaving
    strips under a millimetre thick on the wrong tile. Above the floor, find each
    tile's footprint that is thinner than MIN_WALL within SEAM_BAND of its edge,
    and give it to the neighbouring zone it touches most. Returns the adjusted
    zones for everything above the floor."""
    above = box(-2000, 2000, -2000, 2000, FLOOR_T + 0.01, TOP + 50)
    out = dict(zs)
    moves = []
    for name, z in zs.items():
        foot = (flat ^ above ^ extrude_xy(z, -1.0, TOP + 50)).project()
        r = MIN_WALL / 2
        thin = foot - foot.offset(-r, JoinType.Miter, 2.0).offset(r, JoinType.Miter, 2.0)
        thin ^= z - z.offset(-SEAM_BAND, JoinType.Miter, 2.0)
        for piece in thin.decompose():
            if piece.area() < 0.05:
                continue
            grown = piece.offset(0.3, JoinType.Miter, 2.0)
            near = [(o, (grown ^ zo).area()) for o, zo in zs.items() if o != name]
            other, overlap = max(near, key=lambda t: t[1])
            if overlap > 0:
                moves.append((name, other, grown ^ z))
    for src, dst, cs in moves:
        out[src] = out[src] - cs
        out[dst] = out[dst] + cs
    return out


def build():
    floor, walls = build_shell()
    floor -= details.floor_cuts()
    walls -= details.wall_cuts()
    flat = floor + walls + details.build_props()

    zs = zones()
    upper = _slivers(flat, zs)
    below = box(-2000, 2000, -2000, 2000, -1.0, FLOOR_T + 0.01)
    above = box(-2000, 2000, -2000, 2000, FLOOR_T + 0.01, TOP + 50)
    parts = {}
    for name, z in zs.items():
        # Pull every edge in by a hair: a wall face lying exactly on a seam would
        # otherwise leave a zero-thickness sheet of that wall standing on this tile.
        lo = z.offset(-SEAM_GAP, JoinType.Miter, 2.0)
        hi = upper[name].offset(-SEAM_GAP, JoinType.Miter, 2.0)
        piece = (flat ^ below ^ extrude_xy(lo, -1.0, TOP + 50)) + \
            (flat ^ above ^ extrude_xy(hi, -1.0, TOP + 50))
        # Drop zero-volume slivers left where a wall face lies exactly on a seam.
        piece = union([p for p in piece.decompose() if p.volume() > 1.0])
        if not piece.is_empty():
            parts[f"tile_{name}"] = (piece, UP)
    painting = details.painting_plaque()
    parts["cyber_lich_painting"] = (painting, details.painting_up())
    return flat + painting, parts


def seam_slivers(parts) -> list[str]:
    """Anything above a tile's floor that is thinner than MIN_WALL within 1.5 mm of
    the tile's edge (a sliver a seam has shaved off a neighbouring wall), and any
    part of the floor slab thinner than that. Zero-thickness sheets are caught
    separately by the export report (printcheck.sheet_area)."""
    above = box(-2000, 2000, -2000, 2000, FLOOR_T + 0.5, TOP + 50)
    floor = box(-2000, 2000, -2000, 2000, 0.0, 1.0)
    r = MIN_WALL / 2
    found = []
    for name, (m, _) in parts.items():
        if not name.startswith("tile_"):
            continue
        foot = (m ^ above).project()
        thin = foot - foot.offset(-r, JoinType.Miter, 2.0).offset(r, JoinType.Miter, 2.0)
        edge = (m ^ floor).project()
        thin ^= edge - edge.offset(-1.5, JoinType.Miter, 2.0)
        found += [f"{name}: {c.area():.1f} mm2 at {c.bounds()[:2]}" for c in thin.decompose() if c.area() > 0.2]
        # The floor itself, below its grooves: strips of slab left outside a wall.
        slab = m.slice(FLOOR_T / 2)
        fins = slab - slab.offset(-r, JoinType.Miter, 2.0).offset(r, JoinType.Miter, 2.0)
        # (Under 1 mm2 is rounding noise from the offsets along diagonal edges.)
        found += [f"{name}: floor strip {c.area():.1f} mm2 at {c.bounds()[:2]}" for c in fins.decompose()
                  if c.area() > 1.0]
    return found


def main(out_dir: str = str(OUT_DIR)) -> None:
    assembled, parts = build()
    export_parts(assembled, parts, out_dir, "penthouse")
    total = sum(m.volume() for m, _ in parts.values())
    print(f"assembled {assembled.volume() / 1000:.1f} cm3, parts sum {total / 1000:.1f} cm3")
    slivers = seam_slivers(parts)
    print("seam slivers: " + ("none" if not slivers else "\n  !! ".join([""] + slivers)))


if __name__ == "__main__":
    main(*sys.argv[1:])
