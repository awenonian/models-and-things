"""Furniture and fittings for the penthouse.

Every prop is built in its own frame: centred on the origin, standing on z = 0,
with its front facing +Y. `place()` in details.py turns and drops it on the floor.
Everything prints in place on its floor tile, so nothing may overhang more than
45 degrees: furniture is blocky (pedestals with 45-degree flares instead of legs),
and anything that spans a gap (ring ropes, cage rails, shelves) bridges less than
30 mm.
"""

from __future__ import annotations

import math
import random

from manifold3d import Manifold

from modelkit.csg import box, circle_pts, cyl, extrude_xy, extrude_xz, extrude_yz, section, sphere, union

G = 0.8   # groove width for panel lines


def hull(*ms: Manifold) -> Manifold:
    return Manifold.batch_hull(list(ms))


def frustum_block(w0, d0, w1, d1, z0, z1) -> Manifold:
    """Box tapering from w0 x d0 at z0 to w1 x d1 at z1 (keep the taper <= 45 deg)."""
    return hull(box(-w0 / 2, w0 / 2, -d0 / 2, d0 / 2, z0, z0 + 0.01),
                box(-w1 / 2, w1 / 2, -d1 / 2, d1 / 2, z1 - 0.01, z1))


def front_grooves(w, d, h, xs=(), zs=(), z0=1.0, z1=None, x0=None, x1=None) -> Manifold:
    """Panel lines cut into the +Y face of a w x d box (vertical at xs, horizontal at zs)."""
    z1 = h - 1.0 if z1 is None else z1
    x0 = -w / 2 + 1.0 if x0 is None else x0
    x1 = w / 2 - 1.0 if x1 is None else x1
    cuts = [box(x - G / 2, x + G / 2, d / 2 - 0.5, d / 2 + 1, z0, z1) for x in xs]
    cuts += [box(x0, x1, d / 2 - 0.5, d / 2 + 1, z - G / 2, z + G / 2) for z in zs]
    return union(cuts)


# ---------------------------------------------------------------------------
# Living
# ---------------------------------------------------------------------------


def bed(w: float, l: float, h: float = 7.0, head: float = 15.0, pillows: int = 2) -> Manifold:
    """Headboard at -Y, foot toward +Y."""
    y0, y1 = -l / 2, l / 2
    m = box(-w / 2, w / 2, y0 + 2.5, y1, 0, h - 1.5)                      # base
    m += box(-w / 2 + 0.6, w / 2 - 0.6, y0 + 2.5, y1 - 0.6, h - 1.5, h)    # mattress
    m += box(-w / 2 - 0.5, w / 2 + 0.5, y0, y0 + 2.5, 0, head)            # headboard
    m -= box(-w / 2 + 2, w / 2 - 2, y0 + 2.0, y0 + 3.0, h + 1, head - 2)  # its panel
    pw = (w - 4 - (pillows - 1) * 1.5) / pillows
    for i in range(pillows):
        x = -w / 2 + 2 + i * (pw + 1.5)
        m += hull(box(x, x + pw, y0 + 3.5, y0 + 11, h, h + 1.0),
                  box(x + 0.8, x + pw - 0.8, y0 + 4.3, y0 + 10.2, h, h + 2.4))
    # Blanket over the lower part, turned down at the top.
    yb = y0 + l * 0.38
    m += box(-w / 2, w / 2, yb, y1, h - 2.0, h + 0.8)
    m += box(-w / 2, w / 2, yb, yb + 3.0, h - 2.0, h + 1.4)
    return m


def nightstand(w=10.0, d=9.0, h=9.0) -> Manifold:
    m = box(-w / 2, w / 2, -d / 2, d / 2, 0, h)
    m -= front_grooves(w, d, h, zs=(h * 0.55,))
    m += box(-1, 1, d / 2, d / 2 + 0.8, h * 0.72, h * 0.72 + 1.2)
    return m


def incense() -> Manifold:
    """Dish with a burning stick."""
    return cyl(2.2, 0, 0.8, segments=20) + cyl(0.55, 0.8, 7.0, segments=10)


def bottle(r=1.4, h=5.0) -> Manifold:
    return cyl(r, 0, h, segments=16) + cyl(r * 0.5, h, h + 1.6, segments=12)


def wardrobe(w: float, d: float = 11.0, h: float = 22.0, doors: int = 2) -> Manifold:
    m = box(-w / 2, w / 2, -d / 2, d / 2, 0, h)
    xs = [-w / 2 + w * i / doors for i in range(1, doors)]
    m -= front_grooves(w, d, h, xs=xs, z0=1.5, z1=h - 1.5)
    for x in xs:
        for s in (-1, 1):
            m += box(x + s * 1.5 - 0.5, x + s * 1.5 + 0.5, d / 2, d / 2 + 0.8, h * 0.45, h * 0.62)
    return m


def dresser(w: float, d: float = 10.0, h: float = 11.0, rows: int = 3) -> Manifold:
    m = box(-w / 2, w / 2, -d / 2, d / 2, 0, h)
    zs = [1.0 + (h - 2.0) * i / rows for i in range(1, rows)]
    m -= front_grooves(w, d, h, xs=(0.0,), zs=zs)
    for i in range(rows):
        z = 1.0 + (h - 2.0) * (i + 0.5) / rows
        for x in (-w / 4, w / 4):
            m += box(x - 1.5, x + 1.5, d / 2, d / 2 + 0.7, z - 0.5, z + 0.5)
    return m


def sofa(l: float, d: float = 13.0, seat: float = 6.0, back: float = 12.0, arms: bool = True) -> Manifold:
    m = box(-l / 2, l / 2, -d / 2, d / 2, 0, seat)
    m += box(-l / 2, l / 2, -d / 2, -d / 2 + 3.5, 0, back)
    if arms:
        for s in (-1, 1):
            x0, x1 = sorted((s * l / 2, s * (l / 2 - 2.5)))
            m += box(x0, x1, -d / 2, d / 2, 0, seat + 3)
    # Cushion seams.
    n = max(1, round(l / 16))
    for i in range(1, n):
        x = -l / 2 + l * i / n
        m -= box(x - G / 2, x + G / 2, -d / 2 + 3.5, d / 2 + 1, seat - 0.6, seat + 1)
    return m


def armchair() -> Manifold:
    return sofa(15.0, 13.0)


def chair() -> Manifold:
    """Blocky dining chair, back toward -Y."""
    m = frustum_block(7.0, 7.0, 8.5, 8.5, 0, 5.8)
    m += box(-4.25, 4.25, -4.25, 4.25, 5.8, 6.5)
    m += box(-4.25, 4.25, -4.25, -2.6, 6.5, 14.0)
    return m


def stool() -> Manifold:
    return cyl(2.4, 0, 8.0, segments=20, r_top=3.0) + cyl(3.4, 8.0, 9.0, segments=24)


def pedestal_table(w: float, d: float, h: float, top: float = 1.6, flare: float = 5.0) -> Manifold:
    """Table on a solid pedestal that flares out at 45 degrees to the top's edge."""
    rise = flare * 1.15                      # a little steeper than 45 degrees
    m = box(-w / 2 + flare, w / 2 - flare, -d / 2 + flare, d / 2 - flare, 0, h - top - rise)
    m += frustum_block(w - 2 * flare, d - 2 * flare, w, d, h - top - rise, h - top)
    m += box(-w / 2, w / 2, -d / 2, d / 2, h - top, h)
    m += box(-w / 2 + flare - 1.5, w / 2 - flare + 1.5, -d / 2 + flare - 1.5, d / 2 - flare + 1.5, 0, 1.2)
    return m


def round_table(r: float, h: float) -> Manifold:
    m = cyl(r * 0.35, 0, h - 1.6 - r * 0.7, segments=32)
    m += cyl(r * 0.35, h - 1.6 - r * 0.75, h - 1.6, r_top=r, segments=40)
    m += cyl(r, h - 1.6, h, segments=40)
    m += cyl(r * 0.55, 0, 1.2, segments=32)
    return m


def lounger(l: float = 30.0, w: float = 12.0) -> Manifold:
    """Pool lounger, head end raised toward -Y."""
    m = box(-w / 2, w / 2, -l / 2, l / 2, 0, 4.0)
    m += hull(box(-w / 2, w / 2, -l / 2, -l / 2 + 10, 4.0, 4.1),
              box(-w / 2, w / 2, -l / 2, -l / 2 + 2.5, 10.5, 10.6))
    for y in range(int(-l / 2 + 12), int(l / 2 - 1), 3):
        m -= box(-w / 2 + 1, w / 2 - 1, y, y + G, 3.4, 5)
    return m


def plant(r: float = 5.0, h: float = 7.0, leaves: int = 7, leaf_h: float = 12.0, seed: int = 1) -> Manifold:
    """Pot with spiky leaves (each leans < 40 degrees, so no overhang)."""
    rnd = random.Random(seed)
    m = cyl(r * 0.8, 0, h, r_top=r, segments=28)
    m += cyl(r, h - 1.2, h, segments=28)
    m -= cyl(r - 1.0, h - 0.8, h + 1, segments=28)
    m += cyl(r - 1.0, 0.5, h - 0.8, segments=28)       # soil
    for i in range(leaves):
        a = 2 * math.pi * (i / leaves + rnd.uniform(-0.05, 0.05))
        lean = rnd.uniform(0.35, 0.7)                     # horizontal / vertical
        lh = leaf_h * rnd.uniform(0.7, 1.0)
        dx, dy = math.cos(a) * lean * lh, math.sin(a) * lean * lh
        base = box(-1.0, 1.0, -0.6, 0.6, h - 1.5, h - 1.4).rotate((0, 0, math.degrees(a) + 90))
        tip = box(-0.3, 0.3, -0.3, 0.3, h - 1.4 + lh, h - 1.3 + lh).translate((dx, dy, 0))
        m += hull(base, tip)
    return m


def rug(rx: float, ry: float) -> Manifold:
    m = extrude_xy(section([(rx * math.cos(t), ry * math.sin(t))
                            for t in [2 * math.pi * i / 64 for i in range(64)]]), 0, 0.6)
    inner = section([((rx - 3) * math.cos(t), (ry - 3) * math.sin(t))
                     for t in [2 * math.pi * i / 64 for i in range(64)]])
    return m - extrude_xy(inner - inner.offset(-G), 0.2, 1.0)


# ---------------------------------------------------------------------------
# Kitchen and bathrooms
# ---------------------------------------------------------------------------


def counter(w: float, d: float = 13.0, h: float = 10.0, sink_x=None, hob_x=None, doors: int = 0) -> Manifold:
    m = box(-w / 2, w / 2, -d / 2, d / 2 - 1.0, 0, h - 1.0)
    m += box(-w / 2, w / 2, -d / 2, d / 2, h - 1.0, h)            # worktop, 1 mm lip
    n = doors or max(1, round(w / 12))
    xs = [-w / 2 + w * i / n for i in range(1, n)]
    m -= front_grooves(w, d - 2.0, h - 1.0, xs=xs, z0=1.5, z1=h - 2.2)
    for i in range(n):
        x = -w / 2 + w * (i + 0.5) / n
        m += box(x - 2, x + 2, d / 2 - 1.0, d / 2 - 0.3, h - 3.4, h - 2.6)
    if sink_x is not None:
        m -= box(sink_x - 5, sink_x + 5, -d / 2 + 2.5, d / 2 - 2.5, h - 2.0, h + 1)
        m += box(sink_x - 0.7, sink_x + 0.7, -d / 2 + 0.8, -d / 2 + 2.2, h, h + 4)
        m += box(sink_x - 0.7, sink_x + 0.7, -d / 2 + 0.8, -d / 2 + 4.2, h + 3.0, h + 4)
    if hob_x is not None:
        m += box(hob_x - 7, hob_x + 7, -d / 2 + 1.5, d / 2 - 1.5, h, h + 0.4)
        for dx in (-3.5, 3.5):
            for dy in (-2.6, 2.6):
                ring = cyl(2.0, h + 0.2, h + 1.0, hob_x + dx, dy, segments=20)
                m -= ring - cyl(1.2, h - 1, h + 2, hob_x + dx, dy, segments=20)
    return m


def screen(w: float, h: float, smile: bool = True) -> Manifold:
    """Smart screen for a wall or appliance face: plate in local (x, z) on the y = 0 plane,
    standing out toward +Y. A little face on it begs for attention."""
    m = extrude_xz(section([(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]), 0, 0.8)
    m -= extrude_xz(section([(-w / 2 + 1, -h / 2 + 1), (w / 2 - 1, -h / 2 + 1),
                             (w / 2 - 1, h / 2 - 1), (-w / 2 + 1, h / 2 - 1)]), 0.4, 2)
    if smile:
        s = min(w, h) / 8
        for x in (-1.6 * s, 1.6 * s):
            m += extrude_xz(section(circle_pts(x, 0.8 * s, 0.7 * s, 12)[:-1]), 0, 0.9)
        arc = circle_pts(0, 0.4 * s, 2.2 * s, 12, 200, 340)
        m += extrude_xz(section(arc + list(reversed(circle_pts(0, 0.4 * s, 1.4 * s, 12, 200, 340)))), 0, 0.9)
    return m


def fridge(w=16.0, d=14.0, h=22.0) -> Manifold:
    m = box(-w / 2, w / 2, -d / 2, d / 2, 0, h)
    m -= box(-G / 2, G / 2, d / 2 - 0.5, d / 2 + 1, 1.0, h - 0.5)          # double doors
    for s in (-1, 1):
        m += box(s * 1.6 - 0.5, s * 1.6 + 0.5, d / 2, d / 2 + 0.9, 7, 15)
    m += screen(5.0, 4.0).translate((-w / 4 - 0.4, d / 2, 17.5))
    return m


def chest_freezer(w=22.0, d=12.0, h=9.0) -> Manifold:
    m = box(-w / 2, w / 2, -d / 2, d / 2, 0, h)
    m -= box(-w / 2 - 1, w / 2 + 1, d / 2 - 0.5, d / 2 + 1, h - 2.2 - G / 2, h - 2.2 + G / 2)
    m -= box(-w / 2 - 1, -w / 2 + 0.5, -d / 2 - 1, d / 2 + 1, h - 2.2 - G / 2, h - 2.2 + G / 2)
    m -= box(w / 2 - 0.5, w / 2 + 1, -d / 2 - 1, d / 2 + 1, h - 2.2 - G / 2, h - 2.2 + G / 2)
    m += box(-4, 4, d / 2, d / 2 + 0.8, h - 1.8, h - 0.8)
    m += screen(4.0, 3.0).translate((w / 2 - 4, d / 2, 3.5))
    return m


def toilet() -> Manifold:
    """Cistern at -Y against the wall."""
    m = box(-4.5, 4.5, -6.5, -3.0, 0, 10.0)
    m += box(-5.0, 5.0, -6.5, -2.5, 9.5, 10.5)
    bowl = section([(3.6 * math.cos(t), 2.5 + 4.6 * math.sin(t)) for t in
                    [2 * math.pi * i / 40 for i in range(40)]])
    m += extrude_xy(bowl, 0, 5.5)
    m -= extrude_xy(bowl.offset(-1.2), 4.5, 6)
    m += box(-3.6, 3.6, -3.2, -1.8, 0, 5.5)
    return m


def vanity(w=14.0, d=8.0, h=9.0) -> Manifold:
    m = box(-w / 2, w / 2, -d / 2, d / 2, 0, h)
    m -= front_grooves(w, d, h, xs=(0.0,), z0=1.5, z1=h - 2.5)
    basin = section([(4 * math.cos(t), 0.5 + 2.6 * math.sin(t)) for t in
                     [2 * math.pi * i / 32 for i in range(32)]])
    m -= extrude_xy(basin, h - 1.6, h + 1)
    m += box(-0.6, 0.6, -d / 2 + 0.4, -d / 2 + 1.6, h, h + 3.0)
    m += box(-0.6, 0.6, -d / 2 + 0.4, -d / 2 + 3.4, h + 2.2, h + 3.0)
    return m


def bathtub(w=52.0, d=16.0, h=7.0) -> Manifold:
    """Long axis along X, taps at -X."""
    m = box(-w / 2, w / 2, -d / 2, d / 2, 0, h)
    m -= hull(box(-w / 2 + 2.2, w / 2 - 2.2, -d / 2 + 2.2, d / 2 - 2.2, h - 0.01, h + 1),
              box(-w / 2 + 4.5, w / 2 - 4.5, -d / 2 + 4, d / 2 - 4, 2.0, 2.01))
    m += box(-w / 2 + 0.4, -w / 2 + 1.6, -0.6, 0.6, h, h + 3)
    return m


def shower_tray(w: float, d: float) -> Manifold:
    m = box(-w / 2, w / 2, -d / 2, d / 2, 0, 1.4)
    m -= box(-w / 2 + 1.5, w / 2 - 1.5, -d / 2 + 1.5, d / 2 - 1.5, 0.8, 2)
    for i in range(-2, 3):
        m += box(i * 1.2 - 0.3, i * 1.2 + 0.3, -1.5, 1.5, 0.8, 1.1)
    return m


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


def crate(w: float, d: float, h: float, slats: bool = True) -> Manifold:
    m = box(-w / 2, w / 2, -d / 2, d / 2, 0, h)
    if slats:
        n = max(2, round(h / 4))
        for i in range(1, n):
            z = h * i / n
            m -= box(-w / 2 - 1, w / 2 + 1, -d / 2 - 1, d / 2 + 1, z - G / 2, z + G / 2) - \
                box(-w / 2 + 0.6, w / 2 - 0.6, -d / 2 + 0.6, d / 2 - 0.6, 0, h)
    else:
        m -= box(-w / 2 - 1, w / 2 + 1, -0.4, 0.4, h - 0.5, h + 1)       # parcel tape
    return m


def box_stack(spec, seed=0) -> Manifold:
    """spec: list of (x, y, w, d, h, angle) boxes; each stacked on whatever is below
    (z is found from the earlier boxes it overlaps)."""
    out: list[tuple[Manifold, float]] = []          # (box, top z)
    for x, y, w, d, h, a in spec:
        m = crate(w, d, h, slats=(seed + len(out)) % 3 == 0).rotate((0, 0, a)).translate((x, y, 0))
        foot = m.project()
        below = [(o, top) for o, top in out if (o.project() ^ foot).area() > 1.0]
        z = max((top for _, top in below), default=0.0)
        m = m.translate((0, 0, z))
        if z > 0:
            # Trim the box to the footprint of whatever it rests on: nothing overhangs.
            support = union([o for o, top in below if top >= z - 1e-6])
            m ^= extrude_xy(support.project(), z, z + h + 1)
        out.append((m, z + h))
    return union(o for o, _ in out)


def shelf_unit(w: float, d: float = 9.0, h: float = 22.0, shelves=(7.5, 15.0)) -> Manifold:
    """Open shelving, back at -Y. Shelves bridge between the sides (keep w < 30)."""
    m = box(-w / 2, -w / 2 + 1.4, -d / 2, d / 2, 0, h) + box(w / 2 - 1.4, w / 2, -d / 2, d / 2, 0, h)
    m += box(-w / 2, w / 2, -d / 2, -d / 2 + 1.2, 0, h)
    m += box(-w / 2, w / 2, -d / 2, d / 2, 0, 1.2)
    for z in shelves:
        m += box(-w / 2, w / 2, -d / 2, d / 2, z - 1.2, z)
    m += box(-w / 2, w / 2, -d / 2, d / 2, h - 1.2, h)
    return m


def books(n: int, x0: float, y: float, z: float, seed: int = 0, depth: float = 6.0) -> Manifold:
    """A row of books standing on a shelf, spines toward +Y."""
    rnd = random.Random(seed)
    out, x = [], x0
    for _ in range(n):
        t = rnd.uniform(1.2, 2.2)
        hh = rnd.uniform(4.0, 6.0)
        out.append(box(x, x + t, y - depth / 2, y + depth / 2 - rnd.uniform(0, 0.8), z, z + hh))
        x += t + 0.15
    return union(out)


def pot(r: float, h: float) -> Manifold:
    m = cyl(r, 0, h, segments=24) - cyl(r - 0.7, 0.8, h + 1, segments=24)
    return m + box(r - 0.3, r + 3.0, -0.5, 0.5, h - 1.5, h - 0.5)


def backpack() -> Manifold:
    m = hull(box(-3.5, 3.5, -2.2, 2.2, 0, 0.1), box(-3.0, 3.0, -2.0, 2.0, 7.5, 7.6),
             box(-2.2, 2.2, -1.5, 1.5, 8.8, 9.0))
    m += box(-2.6, 2.6, 2.0, 3.2, 0.8, 4.5)                    # front pocket
    m += box(-1.8, -1.0, -2.6, -2.0, 1.0, 8.0) + box(1.0, 1.8, -2.6, -2.0, 1.0, 8.0)   # straps
    return m


def clothes_rack(w: float, h: float = 21.0, seed: int = 4) -> Manifold:
    """Two end posts and a rail, with long coats and suits hanging to the floor."""
    rnd = random.Random(seed)
    m = box(-w / 2, -w / 2 + 1.5, -1.0, 1.0, 0, h) + box(w / 2 - 1.5, w / 2, -1.0, 1.0, 0, h)
    m += box(-w / 2 - 1, -w / 2 + 2.5, -3.5, 3.5, 0, 1.2) + box(w / 2 - 2.5, w / 2 + 1, -3.5, 3.5, 0, 1.2)
    m += box(-w / 2, w / 2, -0.6, 0.6, h - 1.2, h)
    x = -w / 2 + 3.0
    while x < w / 2 - 4:
        t = rnd.uniform(1.4, 2.4)
        top = h - 1.2
        coat = hull(box(x, x + t, -1.0, 1.0, top - 0.1, top), box(x, x + t, -4.0, 4.0, top - 3.5, top - 3.4),
                    box(x, x + t, -4.5, 4.5, rnd.uniform(1.5, 6.0), rnd.uniform(6.0, 8.0)))
        # Long garments reach the floor so nothing hangs in mid-air.
        m += coat + box(x, x + t, -4.5, 4.5, 0, 6.0)
        x += t + 0.4
    return m


# ---------------------------------------------------------------------------
# Gym, spa, sauna, sensory deprivation
# ---------------------------------------------------------------------------


def boxing_ring(size: float = 76.0, deck: float = 4.0) -> Manifold:
    """Raised ring; posts every third of a side so the ropes bridge < 25 mm."""
    s = size / 2
    m = box(-s, s, -s, s, 0, deck)
    posts = []
    n = 3
    for i in range(n + 1):
        a = -s + 2 + (2 * s - 4) * i / n
        for (x, y) in ((a, -s + 2), (a, s - 2), (-s + 2, a), (s - 2, a)):
            corner = abs(abs(x) - (s - 2)) < 0.1 and abs(abs(y) - (s - 2)) < 0.1
            r = 1.6 if corner else 0.9
            posts.append(cyl(r, deck, deck + (19.0 if corner else 16.0), x, y, segments=16))
            if corner:
                posts.append(cyl(2.0, deck + 17.0, deck + 19.0, x, y, segments=16))   # pads
    m += union(posts)
    ropes = []
    for z in (6.0, 10.5, 15.0):
        zz = deck + z
        for sgn in (-1, 1):
            ropes.append(box(-s + 2, s - 2, sgn * (s - 2) - 0.6, sgn * (s - 2) + 0.6, zz - 0.6, zz + 0.6))
            ropes.append(box(sgn * (s - 2) - 0.6, sgn * (s - 2) + 0.6, -s + 2, s - 2, zz - 0.6, zz + 0.6))
    m += union(ropes)
    # Steps up at one corner.
    m += box(s - 14, s, s, s + 4, 0, deck * 0.5)
    return m


def hex_dumbbell(length: float, r: float) -> Manifold:
    """Lying along X, flat hex faces down."""
    hexa = section([(r * math.cos(math.radians(30 + 60 * i)), r * math.sin(math.radians(30 + 60 * i)))
                    for i in range(6)])
    head = extrude_yz(hexa, 0, r * 0.9).translate((0, 0, r * math.sin(math.radians(60))))
    m = head.translate((-length / 2, 0, 0)) + head.translate((length / 2 - r * 0.9, 0, 0))
    hz = r * math.sin(math.radians(60))
    m += box(-length / 2, length / 2, -0.6, 0.6, hz - 0.6, hz + 0.6)
    return m


def weight_rack(w: float = 44.0, d: float = 10.0) -> Manifold:
    """Two-tier dumbbell rack, back at -Y."""
    m = box(-w / 2, -w / 2 + 2, -d / 2, d / 2, 0, 12) + box(w / 2 - 2, w / 2, -d / 2, d / 2, 0, 12)
    m += box(-1, 1, -d / 2, d / 2, 0, 12)
    m += box(-w / 2, w / 2, -d / 2, d / 2, 4.0, 5.0)
    m += hull(box(-w / 2, w / 2, -d / 2, -d / 2 + 2, 10.0, 11.0), box(-w / 2, w / 2, -d / 2, -d / 2 + 4.5, 11.0, 12.0))
    bells = []
    x = -w / 2 + 4.5
    sizes = [1.6, 1.8, 2.0, 2.2, 2.4]
    i = 0
    while x < w / 2 - 4:
        r = sizes[i % len(sizes)]
        if abs(x) > r + 1.5:
            bells.append(hex_dumbbell(d - 2, r).rotate((0, 0, 90)).translate((x, 0, 5.0)))
        x += 2 * r + 1.2
        i += 1
    return m + union(bells)


def plate_tree() -> Manifold:
    m = cyl(5.0, 0, 1.4, segments=28) + cyl(0.9, 0, 16, segments=12)
    z = 1.4
    for r, t in ((4.6, 1.2), (4.6, 1.2), (3.8, 1.0), (3.0, 1.0), (2.4, 0.9)):
        m += cyl(r, z, z + t, segments=28)
        m -= cyl(r + 1, z + t - 0.2, z + t, segments=28) - cyl(r - 0.4, z, z + t, segments=28)
        z += t
    return m


def heavy_bag() -> Manifold:
    return cyl(6.0, 0, 2.5, segments=28) + cyl(4.2, 2.5, 24.0, segments=28) + cyl(4.6, 6.0, 7.0, segments=28) \
        + cyl(4.6, 20.0, 21.0, segments=28)


def flat_bench(l: float = 28.0) -> Manifold:
    """Along Y."""
    m = box(-1.8, 1.8, -l / 2 + 2, l / 2 - 2, 0, 3.0)
    m += frustum_block(3.6, l - 4, 8.0, l, 3.0, 5.8)
    m += box(-4.0, 4.0, -l / 2, l / 2, 5.8, 7.5)
    m -= box(-5, 5, -l / 2 + 9.5, -l / 2 + 9.5 + G, 7.0, 8)          # seat / back pad split
    return m


def sauna_bench(l: float, d: float, h: float) -> Manifold:
    """Slatted bench, long along X."""
    m = box(-l / 2, l / 2, -d / 2, d / 2, 0, h)
    n = max(2, round(d / 3))
    for i in range(1, n):
        y = -d / 2 + d * i / n
        m -= box(-l / 2 + 1, l / 2 - 1, y - G / 2, y + G / 2, h - 0.6, h + 1)
    return m


def sauna_stove(w: float = 13.0) -> Manifold:
    m = box(-w / 2, w / 2, -w / 2, w / 2, 0, 8.0)
    m += box(-w / 2, w / 2, -w / 2, w / 2, 8.0, 9.0) - box(-w / 2 + 1, w / 2 - 1, -w / 2 + 1, w / 2 - 1, 8.5, 10)
    rnd = random.Random(7)
    stones = []
    for i in range(14):
        x, y = rnd.uniform(-w / 2 + 2.5, w / 2 - 2.5), rnd.uniform(-w / 2 + 2.5, w / 2 - 2.5)
        stones.append(sphere(rnd.uniform(1.5, 2.2), x, y, 8.6, 16))
    m += union(stones) ^ box(-w, w, -w, w, 8.0, 20)
    for y in (-2.5, 0.0, 2.5):
        m -= box(-w / 2 + 2, w / 2 - 2, w / 2 - 0.5, w / 2 + 1, 3.0 + y * 0.6 - 0.4 + 1, 3.0 + y * 0.6 + 0.4 + 1)
    return m


def bucket() -> Manifold:
    m = cyl(2.8, 0, 5.0, r_top=3.4, segments=24) - cyl(2.2, 1.0, 6, r_top=2.8, segments=24)
    return m + cyl(0.6, 1.0, 9.0, 1.5, 0, segments=8)                           # ladle handle


def towels(n: int = 3) -> Manifold:
    return union(box(-4 + 0.3 * (i % 2), 4 + 0.3 * (i % 2), -3, 3, i * 1.4, (i + 1) * 1.4)
                 for i in range(n))


def float_pod(l: float = 64.0, w: float = 26.0, h: float = 10.0) -> Manifold:
    """The 'water coffin': a sealed flotation tank, long along X."""
    r = w / 2
    stadium = section([(-l / 2 + r + r * math.cos(t), r * math.sin(t))
                       for t in [math.pi / 2 + math.pi * i / 24 for i in range(25)]] +
                      [(l / 2 - r + r * math.cos(t), r * math.sin(t))
                       for t in [-math.pi / 2 + math.pi * i / 24 for i in range(25)]])
    m = extrude_xy(stadium, 0, h - 2.5)
    m += hull(extrude_xy(stadium, h - 2.5, h - 2.4), extrude_xy(stadium.offset(-2.0), h, h + 0.1))
    # Hinge line and a porthole on the lid.
    m -= box(-l / 2 + 8, l / 2 - 8, -0.4, 0.4, h - 0.2, h + 1)
    m += cyl(3.0, h - 0.5, h + 0.6, -l / 2 + r, 0, segments=24)
    m -= cyl(2.2, h + 0.2, h + 1, -l / 2 + r, 0, segments=24)
    return m


def control_panel() -> Manifold:
    """Small pedestal console."""
    return box(-3, 3, -2, 2, 0, 9) + hull(box(-3.5, 3.5, -2.5, 2.5, 9, 9.1), box(-3.5, 3.5, -1.0, 2.5, 11, 11.1))


# ---------------------------------------------------------------------------
# Dining room, holo space
# ---------------------------------------------------------------------------


def platter(r: float) -> Manifold:
    return cyl(r, 0, 0.8, segments=32) - cyl(r - 0.8, 0.5, 1, segments=32)


def oysters(r: float = 6.0) -> Manifold:
    m = platter(r)
    for i in range(7):
        a = 2 * math.pi * i / 7
        x, y = (r - 2.2) * math.cos(a), (r - 2.2) * math.sin(a)
        m += sphere(1.4, x, y, 0.4, 12) ^ box(-r, r, -r, r, 0.4, 4)
    m += sphere(1.6, 0, 0, 0.4, 12) ^ box(-r, r, -r, r, 0.4, 4)        # lemon
    return m


def burgers(r: float = 6.0) -> Manifold:
    m = platter(r)
    for (x, y) in ((-2.4, -1.6), (2.4, -1.6), (0, 2.4)):
        m += cyl(1.8, 0.4, 1.4, x, y, segments=16) + cyl(2.0, 1.4, 2.0, x, y, segments=16) \
            + cyl(1.9, 2.0, 2.6, x, y, segments=16, r_top=1.2)
    return m


def hotdogs() -> Manifold:
    m = box(-6, 6, -4, 4, 0, 0.8)
    for y in (-2.2, 0.0, 2.2):
        m += box(-4.5, 4.5, y - 0.8, y + 0.8, 0.8, 1.6)
        bun = extrude_yz(section(circle_pts(y, 1.55, 0.8, 12, 0, 180)), -4.5, 4.5)   # overlaps the sausage
        m += bun
        m += box(-5.2, 5.2, y - 0.45, y + 0.45, 1.6, 2.4)
    return m


def plate(r: float = 2.6) -> Manifold:
    return cyl(r, 0, 0.6, segments=20)


def glass(r: float = 0.9, h: float = 3.0) -> Manifold:
    return cyl(r, 0, h, segments=14) - cyl(r - 0.4, 0.8, h + 1, segments=14)


def cans(n: int = 6, r: float = 1.1, h: float = 3.2) -> Manifold:
    out = []
    for i in range(n):
        x = (i % 3 - 1) * (2 * r + 0.15)
        y = (i // 3 - 0.5) * (2 * r + 0.15)
        out.append(cyl(r, 0, h, x, y, segments=16) + cyl(r * 0.8, h, h + 0.3, x, y, segments=16))
    return union(out)


def bowl(r: float = 5.0) -> Manifold:
    return cyl(r * 0.75, 0, 2.5, r_top=r, segments=28) - cyl(r * 0.6, 0.8, 3, r_top=r - 0.8, segments=28)


def bone(l: float = 9.0) -> Manifold:
    """Lying flat (half-round ends sit on the floor)."""
    m = box(-l / 2 + 1, l / 2 - 1, -0.7, 0.7, 0, 1.2)
    for x in (-l / 2 + 1, l / 2 - 1):
        for y in (-0.8, 0.8):
            m += cyl(1.0, 0, 1.4, x, y, segments=12)
    return m


def holo_emitter() -> Manifold:
    m = cyl(3.2, 0, 1.2, segments=24, r_top=2.6) + cyl(1.0, 1.2, 3.0, segments=12)
    m += cyl(1.0, 3.0, 4.05, r_top=2.0, segments=24)                     # 45-degree neck under the dome
    m += sphere(2.0, 0, 0, 4.0, 16) ^ box(-3, 3, -3, 3, 4.0, 7.0)
    return m


def drinks_cabinet(w: float, d: float = 9.0, h: float = 10.0) -> Manifold:
    """Low cabinet with a glass-fronted fridge and bottles on top."""
    m = box(-w / 2, w / 2, -d / 2, d / 2, 0, h)
    m -= box(-w / 2 + 1.5, -1.0, d / 2 - 0.8, d / 2 + 1, 1.5, h - 1.5)
    for i in range(4):
        x = -w / 2 + 3.5 + i * 3.2
        if x < -2.5:
            m += cyl(1.0, 1.5, 4.5, x, d / 2 - 2.0, segments=12)
            m += cyl(1.0, 5.5, 8.5, x, d / 2 - 2.0, segments=12)
    m += box(-w / 2 + 1.5, -1.0, d / 2 - 2.6, d / 2 - 0.8, 5.0, 5.5)
    m -= front_grooves(w, d, h, xs=(w / 4,), x0=0.0, z0=1.5, z1=h - 1.5)
    for k, x in enumerate((2.0, 5.0, 8.0)):
        if x < w / 2 - 1.5:
            m += bottle(1.0, 4.0 + k).translate((x, -1, h))
    return m


# ---------------------------------------------------------------------------
# Hallway, corridor
# ---------------------------------------------------------------------------


def console_table(w: float = 40.0, d: float = 8.0, h: float = 10.0) -> Manifold:
    m = pedestal_table(w, d, h, top=1.4, flare=2.5)
    m += bowl(2.6).translate((-w / 4, 0, h))
    m += plant(2.4, 3.0, 5, 6.0, seed=5).translate((w / 3, 0, h))
    return m


def doormat(w: float = 30.0, d: float = 12.0) -> Manifold:
    m = box(-w / 2, w / 2, -d / 2, d / 2, 0, 0.6)
    for x in range(int(-w / 2 + 2), int(w / 2 - 1), 2):
        m -= box(x, x + 0.8, -d / 2 + 1.2, d / 2 - 1.2, 0.3, 1)
    return m


def stairs(w: float, run: float, steps: int, rise: float) -> Manifold:
    """Flight rising toward +Y, starting at y = -run/2."""
    out = []
    tread = run / steps
    for i in range(steps):
        out.append(box(-w / 2, w / 2, -run / 2 + i * tread, run / 2, 0, (i + 1) * rise))
    m = union(out)
    for i in range(steps):
        y = -run / 2 + i * tread
        m -= box(-w / 2 - 1, w / 2 + 1, y + 0.8, y + 1.6, (i + 1) * rise - 0.4, (i + 1) * rise + 1)
    return m
