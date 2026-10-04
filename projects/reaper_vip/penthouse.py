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

from modelkit.csg import extrude_xy, section, union
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


def build():
    floor, walls = build_shell()
    floor -= details.floor_cuts()
    walls -= details.wall_cuts()
    flat = floor + walls + details.build_props()

    parts = {}
    for name, z in zones().items():
        piece = flat ^ extrude_xy(z, -1.0, TOP + 50)
        # Drop zero-volume slivers left where a wall face lies exactly on a seam.
        piece = union([p for p in piece.decompose() if p.volume() > 1.0])
        if not piece.is_empty():
            parts[f"tile_{name}"] = (piece, UP)
    painting = details.painting_plaque()
    parts["cyber_lich_painting"] = (painting, details.painting_up())
    return flat + painting, parts


def main(out_dir: str = str(OUT_DIR)) -> None:
    assembled, parts = build()
    export_parts(assembled, parts, out_dir, "penthouse")
    total = sum(m.volume() for m, _ in parts.values())
    print(f"assembled {assembled.volume() / 1000:.1f} cm3, parts sum {total / 1000:.1f} cm3")


if __name__ == "__main__":
    main(*sys.argv[1:])
