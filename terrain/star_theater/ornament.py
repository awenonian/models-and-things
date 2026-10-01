"""Ornaments shared by the Star Theater pieces (stage and seating).

All of these are reliefs on a wall face lying in the x/z plane at y = 0 that
faces +y, built so they print face-up without supports.
"""

from __future__ import annotations

import math

from manifold3d import Manifold

from terrain.common.csg import (
    box, circle_pts, extrude_xz, extrude_yz, gear_pts, section, sphere, union,
)


def pilaster(cx: float, z0: float, z_top: float, hw: float = 8.0) -> Manifold:
    """Fluted pilaster with base and capital, standing proud of a wall face at y = 0."""
    p = box(cx - hw, cx + hw, -0.1, 4.0, z0, z_top)
    # Base: two stepped blocks.
    p += box(cx - hw - 2, cx + hw + 2, -0.1, 6.0, z0, z0 + 7)
    p += box(cx - hw - 1, cx + hw + 1, -0.1, 5.0, z0 + 7, z0 + 10)
    # Capital: necking, echinus (45 deg flare -> printable), abacus.
    p += box(cx - hw - 0.5, cx + hw + 0.5, -0.1, 4.6, z_top - 13, z_top - 11)
    flare = section([(-0.1, z_top - 9), (4.6, z_top - 9), (7.0, z_top - 6.5),
                     (7.0, z_top), (-0.1, z_top)])
    p += extrude_yz(flare, cx - hw - 2.5, cx + hw + 2.5)
    # Volutes on the capital (little scroll discs).
    for sx in (-1, 1):
        vol = extrude_xz(section(circle_pts(cx + sx * (hw + 0.5), z_top - 6.5, 2.6, 20)), 0, 7.6)
        vol -= extrude_xz(section(circle_pts(cx + sx * (hw + 0.5), z_top - 6.5, 1.2, 16)), 7, 8)
        p += vol
    # Flutes.
    flutes = []
    for dx in (-4.2, 0, 4.2):
        fx = cx + dx
        groove = section([(fx - 0.9, z0 + 14), (fx + 0.9, z0 + 14),
                          (fx + 0.9, z_top - 17), (fx - 0.9, z_top - 17)]).offset(
            0.0)
        flutes.append(extrude_xz(groove, 2.8, 5))
        flutes.append(sphere(0.9, fx, 4.0, z0 + 14, 10))
        flutes.append(sphere(0.9, fx, 4.0, z_top - 17, 10))
    p -= union(flutes)
    return p


def dove(cx: float, cz: float, size: float, facing: int, y0: float) -> Manifold:
    """Colette's mechanical dove, in relief on the wall face (x, z elevation).

    Drawn in unit coordinates facing +x (~1.0 wide, 0.85 tall), then scaled.
    """
    def cs(pts):
        return section([(cx + facing * x * size, cz + z * size) for (x, z) in pts])

    body_pts = [(0.30 * math.cos(t) * math.cos(0.21) - 0.11 * math.sin(t) * math.sin(0.21),
                 0.30 * math.cos(t) * math.sin(0.21) + 0.11 * math.sin(t) * math.cos(0.21))
                for t in (2 * math.pi * i / 40 for i in range(40))]
    body = (cs(body_pts) + cs(circle_pts(0.30, 0.10, 0.085, 24))
            + cs([(0.12, 0.02), (0.28, 0.03), (0.33, 0.16), (0.18, 0.11)])
            + cs([(0.37, 0.12), (0.47, 0.085), (0.37, 0.065)])
            + cs([(-0.20, -0.02), (-0.52, 0.06), (-0.56, -0.02), (-0.54, -0.10),
                  (-0.50, -0.17), (-0.20, -0.09)]))
    wing_f_pts = [(0.08, 0.05), (0.02, 0.25), (-0.06, 0.45), (-0.20, 0.62), (-0.30, 0.66),
                  (-0.28, 0.56), (-0.36, 0.55), (-0.32, 0.45), (-0.40, 0.42), (-0.32, 0.32),
                  (-0.36, 0.26), (-0.24, 0.16), (-0.16, 0.04)]
    wing_b_pts = [(0.14, 0.08), (0.20, 0.30), (0.20, 0.48), (0.14, 0.62), (0.10, 0.52),
                  (0.06, 0.56), (0.02, 0.44), (-0.02, 0.40), (0.00, 0.20)]
    m = extrude_xz(cs(wing_b_pts), y0, y0 + 1.6)
    m += extrude_xz(body, y0, y0 + 2.6)
    m += extrude_xz(cs(wing_f_pts), y0, y0 + 3.4)
    # Feather lines on the front wing, fanning out from the wing root.
    root = (-0.04, 0.10)
    for tip in [(-0.27, 0.60), (-0.33, 0.50), (-0.35, 0.40), (-0.32, 0.29)]:
        ax_, az_ = cx + facing * root[0] * size, cz + root[1] * size
        bx_, bz_ = cx + facing * tip[0] * size, cz + tip[1] * size
        L = math.hypot(bx_ - ax_, bz_ - az_)
        ang = math.degrees(math.atan2(bz_ - az_, bx_ - ax_))
        line = section([(0, -0.35), (L, -0.35), (L, 0.35), (0, 0.35)]).rotate(ang)
        m -= extrude_xz(line.translate((ax_, az_)), y0 + 2.8, y0 + 5)
    # Clockwork gear at the wing root, and an eye.
    gx, gz = cx + facing * (-0.06) * size, cz + 0.10 * size
    gear = (section(gear_pts(gx, gz, 0.075 * size, 9))
            - section(circle_pts(gx, gz, 0.028 * size, 12)))
    m += extrude_xz(gear, y0, y0 + 4.0)
    ex, ez = cx + facing * 0.31 * size, cz + 0.12 * size
    m -= extrude_xz(section(circle_pts(ex, ez, 0.022 * size, 10)), y0 + 2.0, y0 + 4)
    return m
