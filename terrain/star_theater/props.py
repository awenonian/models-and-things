"""Orchestra-pit furniture for the Star Theater (used by the stage piece)."""

from __future__ import annotations

import math

from manifold3d import Manifold

from terrain.common.csg import box, cyl, extrude_xy, extrude_yz, section


def piano() -> Manifold:
    """Upright piano, keyboard toward +y, origin centre-bottom."""
    m = box(-14, 14, -6, 6, 0, 22)
    m += box(-14.6, 14.6, -6.6, 6.6, 21, 23)                 # lid
    m += box(-15, 15, -6.4, 6.4, 0, 2)                       # plinth
    # Keyboard shelf with a 45-degree cheek underneath (no overhang).
    m += extrude_yz(section([(6, 5), (11, 10), (11, 11.6), (6, 11.6)]), -13, 13)
    for i in range(-5, 6):
        if i in (-2, 1, 4):
            continue
        m += box(i * 2.2 - 0.5, i * 2.2 + 0.5, 6.5, 9.5, 11.6, 12.3)  # black keys
    m += extrude_yz(section([(6, 12), (8.2, 17.5), (7.4, 17.8), (6, 14)]), -9, 9)  # music rack
    # Panels on the front board.
    for x in (-7, 7):
        m -= box(x - 5, x + 5, 5.4, 6.4, 13.5, 20)
    # Candelabra on top.
    m += cyl(0.6, 23, 27, -9, 0, segments=10)
    m += box(-12, -6, -0.5, 0.5, 26.5, 27.3)
    for x in (-12, -9, -6):
        m += cyl(0.8, 27, 29.5, x, 0, segments=10)
    return m


def music_stand() -> Manifold:
    """Stand facing +y, origin on the floor."""
    m = cyl(3.0, 0, 1.0, segments=20) + cyl(0.75, 0, 14, segments=10)
    desk = box(-5.5, 5.5, -0.5, 0.5, 0, 8).rotate((-30, 0, 0)).translate((0, 0.6, 13.0))
    lip = box(-5.5, 5.5, -0.2, 1.8, -0.9, 0).rotate((-30, 0, 0)).translate((0, 0.6, 13.0))
    return m + desk + lip


def stool() -> Manifold:
    return cyl(3.6, 0, 6.5, segments=20) + cyl(4.0, 6.5, 7.6, segments=20)


def podium() -> Manifold:
    oct_ = section([(9 * math.cos(math.pi / 8 + i * math.pi / 4),
                     9 * math.sin(math.pi / 8 + i * math.pi / 4)) for i in range(8)])
    m = extrude_xy(oct_, 0, 3.5) + extrude_xy(oct_.offset(-1.2), 3.5, 4.2)
    m += music_stand().rotate((0, 0, 180)).translate((0, -5.5, 4.2))
    return m


def drum() -> Manifold:
    m = cyl(6.5, 0, 9, segments=32)
    m += cyl(7.0, 0, 1.2, segments=32) + cyl(7.0, 7.8, 9.0, segments=32)
    for i in range(8):
        a = i * math.pi / 4
        m += box(-0.5, 0.5, -0.5, 0.5, 1.2, 7.8).translate((6.6 * math.cos(a), 6.6 * math.sin(a), 0))
    return m
