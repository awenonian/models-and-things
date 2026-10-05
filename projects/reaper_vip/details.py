"""Room contents: furniture, fittings and wall details, placed on the plan.

Positions are map coordinates (see plan.py). `place()` stands a prop on the
floor facing a compass direction on the map (0 = north/up the page, 90 = east).
`mount()` fixes a relief to one face of a wall.

Room notes from the adventure, and what they became:
  Gym           weights and a sparring ring (the cydroid is a mini)
  Shower/Spa    hot-tub pool, shower, loungers, towels, plants
  Sauna         slatted benches, stove with stones, bucket
  Sensory dep.  padded walls, the "water coffin", the lock button outside the door
  Hallway       deliveries piled by the door, console, doormat
  Guest room    closet full of boxes, pots and pans, old books and a tuxedo;
                a dresser for the Faceblock
  Kitchen       Smart(tm) appliances with needy little faces, fridge, freezer
  Master bed    soundproofing panels, wall safe, incense, closet with the backpack
  Storage       crates and shelving
  Dining room   the big cats' cage (bowl, bones), buffet on the table
  Holo space    sofas round a table of canned gin & tonics, holo emitters, and
                the Cyber-Lich painting -- a separate part hiding the safe
  Balcony       glass rail, loveseat, and the section of floor that breaks
"""

from __future__ import annotations

import math
import random

import numpy as np
from manifold3d import CrossSection, Manifold, OpType

from modelkit.csg import box, circle_pts, cyl, extrude_xy, extrude_xz, extrude_yz, section, union
from projects.reaper_vip import plan
from projects.reaper_vip import props as P
from projects.reaper_vip.plan import M
from projects.reaper_vip.shell import (FLOOR_T, GROOVE_D, GROOVE_W, TOP, WALL_H, path_length, point_at,
                                       stroke, wall_path)

FACES = {"n": 0, "e": 90, "s": 180, "w": 270}
WALLS = {w.name: w for w in plan.WALLS}


def place(m: Manifold, x: float, y: float, face=0, z: float = 0.0) -> Manifold:
    """Stand a prop (front toward local +Y) at map (x, y), front facing `face`.
    Props sink GROOVE_D into the floor so they fill the floor's grooves under them
    (and never sit on a seam of coincident faces)."""
    deg = FACES.get(face, face) if isinstance(face, str) else face
    px, py = M(x, y)
    return m.rotate((0, 0, -deg)).translate((px, py, FLOOR_T - GROOVE_D + z))


def wall_frame(name: str, x: float, y: float, toward: tuple[float, float]):
    """Local frame on one face of a wall, at the point nearest map (x, y):
    local x runs along the face, +y points out of it into the room containing
    `toward`, z is height above the floor. Returns a 3x4 matrix."""
    w = WALLS[name]
    path = wall_path(w)
    p = np.asarray(M(x, y))
    best = None
    for i in range(len(path) - 1):
        a, b = np.asarray(path[i]), np.asarray(path[i + 1])
        d = b - a
        s = float(np.clip((p - a) @ d / (d @ d), 0, 1))
        f = a + d * s
        dist = float(np.linalg.norm(p - f))
        if best is None or dist < best[0]:
            best = (dist, f, d / np.linalg.norm(d))
    _, f, u = best
    n = np.array([-u[1], u[0]])
    if (np.asarray(M(*toward)) - f) @ n < 0:
        n = -n
    o = f + n * w.t / 2
    ex = np.array([n[1], -n[0]])          # keeps the frame right-handed
    return np.array([[ex[0], n[0], 0, o[0]],
                     [ex[1], n[1], 0, o[1]],
                     [0, 0, 1, FLOOR_T]], dtype=float)


def mount(m: Manifold, name: str, x: float, y: float, toward) -> Manifold:
    return m.transform(wall_frame(name, x, y, toward))


def along(name: str, x: float, y: float, toward, q: tuple[float, float]) -> float:
    """Local x coordinate (on wall_frame(name, x, y, toward)) of map point q."""
    T = wall_frame(name, x, y, toward)
    return float((np.asarray(M(*q)) - T[:2, 3]) @ T[:2, 0])


def fz(z0: float, z1: float, x0: float, x1: float, y0: float = -0.5, y1: float = 0.8) -> Manifold:
    """Relief block in a wall frame."""
    return box(x0, x1, y0, y1, z0, z1)


def plaque_xz(w: float, h: float, t: float, zc: float, xc: float = 0.0) -> Manifold:
    return box(xc - w / 2, xc + w / 2, -0.5, t, zc - h / 2, zc + h / 2)


# ---------------------------------------------------------------------------
# Wall reliefs
# ---------------------------------------------------------------------------


def neighbour_door() -> Manifold:
    """A closed flat door, cut off with the wall, with a keypad."""
    m = box(-13, -11, -0.5, 1.2, 0, WALL_H) + box(11, 13, -0.5, 1.2, 0, WALL_H)
    m += box(-11, 11, -0.5, 0.4, 0, WALL_H)
    for z in (6.0, 13.0, 20.0):
        m += box(-9, 9, -0.5, 0.8, z - 0.6, z + 0.6) ^ box(-9, 9, -1, 1, 0, WALL_H)
    m += box(7.5, 9.5, 0, 1.4, 11.5, 12.5)                       # handle
    m += box(14.5, 18.5, -0.5, 1.0, 12, 17) - box(15.3, 17.7, 0.6, 2, 15, 16.4)   # keypad
    return m


def call_panel() -> Manifold:
    m = box(-2.5, 2.5, -0.5, 0.8, 9, 17)
    for z in (11.0, 14.5):
        m += box(-0.9, 0.9, 0.5, 1.3, z - 0.9, z + 0.9)
    return m


def handrail(length: float, z: float = 10.0) -> Manifold:
    m = P.hull(box(-length / 2, length / 2, -0.5, 0.1, z - 1.6, z + 0.6),
               box(-length / 2, length / 2, -0.5, 1.2, z - 0.4, z + 0.6))
    for x in (-length / 2 + 3, 0.0, length / 2 - 3):
        m += box(x - 0.6, x + 0.6, -0.5, 1.2, z - 2.5, z)
    return m


def shower_head(z: float = 21.0) -> Manifold:
    m = box(-0.6, 0.6, -0.5, 1.0, 8, z)                            # riser
    disc = section(circle_pts(0, z, 2.6, 24)[:-1])
    m += extrude_xz(disc, -0.5, 1.6)
    m -= union(box(x - 0.3, x + 0.3, 1.2, 2, z - 1.4, z + 1.4) for x in (-1.2, 0, 1.2))
    m += box(-2.0, 2.0, -0.5, 1.4, 9.5, 11.0)                      # mixer
    return m


def wall_safe() -> Manifold:
    m = box(-6.5, 6.5, -0.5, 0.9, 9, 21)
    m -= box(-5.5, 5.5, 0.5, 2, 10, 20)
    m += extrude_xz(section(circle_pts(-1.5, 15, 2.2, 24)[:-1]), -0.5, 1.6)
    m -= box(-1.75, -1.25, 1.2, 2, 15.6, 17.0)                       # dial mark
    m += box(2.2, 3.4, -0.5, 1.6, 12.5, 17.5)                      # handle
    return m


def acoustic_panels(x0: float, x1: float, z0: float = 2.0, z1: float = 24.0,
                    pw: float = 7.0, ph: float = 6.6) -> Manifold:
    """Soundproofing: a grid of chamfered foam panels."""
    out = []
    x = x0
    while x + pw <= x1 + 0.01:
        z = z0
        k = 0
        while z + ph <= z1 + 0.01:
            vertical = (k + round(x / pw)) % 2 == 0
            p = P.hull(box(x, x + pw, -0.5, 0.1, z, z + ph),
                       box(x + 0.6, x + pw - 0.6, -0.5, 0.8, z + 0.6, z + ph - 0.6))
            ribs = [box(x + 1.2 + i * 1.6, x + 1.2 + i * 1.6 + 0.8, 0.4, 1.0, z, z + ph)
                    for i in range(3)] if vertical else \
                [box(x, x + pw, 0.4, 1.0, z + 1.2 + i * 1.6, z + 1.2 + i * 1.6 + 0.8) for i in range(3)]
            out.append(p - union(ribs))
            z += ph + 0.9
            k += 1
        x += pw + 0.9
    return union(out)


def padding(x0: float, x1: float, skip=(), z0: float = 0.6, z1: float = WALL_H - 0.4) -> Manifold:
    """Quilted wall padding for the sensory deprivation chamber."""
    out = []
    pw, ph, gap = 8.0, 7.4, 0.9
    n = max(1, round((x1 - x0) / (pw + gap)))
    pw = (x1 - x0) / n - gap
    for i in range(n):
        xa = x0 + i * (pw + gap) + gap / 2
        xb = xa + pw
        if any(xa < b and xb > a for a, b in skip):
            continue
        z = z0
        while z + ph <= z1 + 0.01:
            out.append(P.hull(box(xa, xb, -0.5, 0.1, z, z + ph),
                              box(xa + 1.0, xb - 1.0, -0.5, 1.1, z + 1.0, z + ph - 1.0)))
            out.append(box((xa + xb) / 2 - 0.5, (xa + xb) / 2 + 0.5, 0.5, 1.5, z + ph / 2 - 0.5, z + ph / 2 + 0.5))
            z += ph + gap
    return union(out)


def lock_button() -> Manifold:
    m = box(-2.5, 2.5, -0.5, 0.8, 11, 18)
    m += box(-1.2, 1.2, 0.5, 1.6, 13.2, 15.6)
    return m


def tuxedo() -> Manifold:
    """Relief of a dinner jacket on a hanger (local x along the wall, z up)."""
    jacket = section([(-5.5, 3.0), (5.5, 3.0), (6.2, 15.5), (3.2, 18.0), (-3.2, 18.0), (-6.2, 15.5)])
    m = extrude_xz(jacket, -0.3, 0.9)
    shirt = section([(-2.4, 18.2), (2.4, 18.2), (0.0, 10.5)])
    m -= extrude_xz(shirt, 0.5, 2)
    m += extrude_xz(section([(-1.6, 16.6), (1.6, 16.6), (1.6, 17.6), (-1.6, 17.6)]), 0.3, 1.2)   # bow tie
    m += extrude_xz(section([(-0.4, 18), (0.4, 18), (0.4, 20.5), (-0.4, 20.5)]), -0.3, 0.8)     # hook
    m -= box(-0.3, 0.3, 0.6, 2, 3.5, 10.5)                           # buttoned front
    return m


# ---------------------------------------------------------------------------
# Built-in pieces
# ---------------------------------------------------------------------------


def hot_tub() -> Manifold:
    """Raised pool between the walls, open to the spa on its south side."""
    x0, x1, y0, y1 = 547.5, 647.5, 103.5, 244.0
    rim_h, water = 7.0, 3.0
    (ax, ay), (bx, by) = M(x0, y1), M(x1, y0)
    outer = box(ax, bx, ay, by, 0, FLOOR_T + rim_h)
    inner = box(ax + 4.5, bx - 4.5, ay + 4.5, by - 4.5, FLOOR_T + water, FLOOR_T + rim_h + 1)
    m = outer - inner
    # Rim coping: a groove 1.5 mm in from the inner edge.
    m -= box(ax + 3.0, bx - 3.0, ay + 3.0, by - 3.0, FLOOR_T + rim_h - 0.5, FLOOR_T + rim_h + 1) - \
        box(ax + 3.8, bx - 3.8, ay + 3.8, by - 3.8, 0, 100)
    # Seat ledge along the north end, steps down from the spa side.
    m += box(ax + 4.5, bx - 4.5, by - 12.0, by - 4.5, 0, FLOOR_T + water + 2.0)
    sx = M(597, 0)[0]
    m += box(sx - 12, sx + 12, ay - 2, ay + 4.5 + 6.0, 0, FLOOR_T + water + 2.0)
    m += box(sx - 12, sx + 12, ay - 3.5, ay + 0.5, 0, FLOOR_T + 1.6)
    # Ripples on the water.
    c = M(615, 160)
    rings = []
    for r in (9, 18, 28, 39):
        arc = circle_pts(c[0], c[1], r, 48)
        ring = section(arc[:-1]) - section(arc[:-1]).offset(-GROOVE_W)
        rings.append(ring)
    water_cs = section([(ax + 4.5, ay + 4.5), (bx - 4.5, ay + 4.5), (bx - 4.5, by - 12), (ax + 4.5, by - 12)])
    ripples = CrossSection.batch_boolean(rings, OpType.Add) ^ water_cs
    m -= extrude_xy(ripples, FLOOR_T + water - 0.4, FLOOR_T + water + 1)
    return m


def cage() -> Manifold:
    """Bars across the dining room, with a padlocked gate."""
    pts = [M(330.0, 625), M(465, 625), M(481.5, 680)]
    out = []
    # rails: bottom (on the floor), middle and top
    for z0, z1 in ((0.0, FLOOR_T + 1.4), (FLOOR_T + 12.0, FLOOR_T + 13.4), (TOP - 1.4, TOP)):
        out.append(extrude_xy(stroke(pts, 1.8), z0, z1))
    L = path_length(pts)
    gate_s = (M(388, 625)[0] - pts[0][0], M(412, 625)[0] - pts[0][0])
    n = int(L / 5.5)
    for i in range(n + 1):
        s = L * i / n
        p, u = point_at(pts, s)
        r = 1.3 if any(abs(s - g) < 2.8 for g in gate_s) else 0.85
        out.append(cyl(r, 0, TOP, p[0], p[1], segments=12))
    # gate posts, a cross brace and the padlock
    for g in gate_s:
        p, u = point_at(pts, g)
        out.append(cyl(1.4, 0, TOP, p[0], p[1], segments=16))
    p, u = point_at(pts, gate_s[1] - 2.5)
    out.append(box(-1.6, 1.6, -1.6, 1.6, FLOOR_T + 9.0, FLOOR_T + 12.0).translate((p[0], p[1], 0)))
    out.append(box(-1.0, 1.0, -1.2, 1.2, FLOOR_T + 12.0, FLOOR_T + 13.0).translate((p[0], p[1], 0)))
    return union(out)


def stair_flight() -> Manifold:
    return place(P.stairs(76.0, 68.0, 6, 3.5), 190, 306, "s")


def weak_floor() -> Manifold:
    """The balcony section that gives way: a jagged outline and cracks, cut into the floor."""
    rnd = random.Random(11)
    cx, cy = 540.0, 707.0
    pts = []
    for i in range(22):
        a = 2 * math.pi * i / 22
        r = rnd.uniform(15, 21) * (1.25 if math.cos(a) ** 2 > 0.5 else 1.0)
        pts.append((cx + r * math.cos(a) * 1.4, cy + r * math.sin(a) * 0.85))
    poly = section([M(*q) for q in pts])
    lines = [poly - poly.offset(-GROOVE_W)]
    for i in range(6):
        a = 2 * math.pi * (i / 6 + rnd.uniform(-0.05, 0.05))
        x, y = cx, cy
        path = [M(x, y)]
        for _ in range(4):
            a += rnd.uniform(-0.5, 0.5)
            step = rnd.uniform(5, 9)
            x, y = x + step * math.cos(a) * 1.3, y + step * math.sin(a) * 0.8
            path.append(M(x, y))
        lines.append(stroke(path, 0.7, cap=False))
    g = CrossSection.batch_boolean(lines, OpType.Add)
    return extrude_xy(g, FLOOR_T - GROOVE_D, FLOOR_T + 1)


# ---------------------------------------------------------------------------
# The Cyber-Lich painting and the safe behind it
# ---------------------------------------------------------------------------

PAINTING_AT = (655.0, 629.6)          # on the holo-space face of the diagonal wall
PAINT_W, PAINT_Z0, PAINT_Z1 = 26.0, 4.5, 23.5
PEG_X, PEG_Z = 10.6, 14.0
PEG_D, PEG_HOLE, PEG_LEN = 2.2, 2.7, 1.8


def _diamond_x_axis(d: float, y0: float, y1: float, x: float, z: float) -> Manifold:
    """Square peg turned 45 degrees (no flat underside), along local y."""
    h = d / 2
    return extrude_xz(section([(x - h, z), (x, z - h), (x + h, z), (x, z + h)]), y0, y1)


def painting_frame():
    toward = (700, 560)
    return wall_frame("holo_diag", *PAINTING_AT, toward)


def safe_niche_cut() -> Manifold:
    """Recess in the wall behind the painting; its top slopes at 45 degrees."""
    prof = section([(0.1, 7.5), (-2.2, 7.5), (-2.2, 18.6), (0.1, 21.3)])     # (y, z)
    niche = extrude_yz(prof, -8.0, 8.0)
    return niche.transform(painting_frame())


def safe_and_pegs() -> Manifold:
    """Safe door inside the niche, and the two pegs the painting hangs on."""
    m = box(-6.8, 6.8, -2.6, -1.4, 8.3, 18.5)
    m -= box(-6.0, 6.0, -1.8, -1.0, 9.1, 17.7) - box(-5.2, 5.2, -2, -1.2, 9.9, 16.9)
    m += extrude_xz(section(circle_pts(-1.5, 13.4, 2.4, 24)[:-1]), -2.0, -0.6)        # dial
    m -= union(box(-1.5 + 2.0 * math.cos(a) - 0.25, -1.5 + 2.0 * math.cos(a) + 0.25, -1.0, 0,
                   13.4 + 2.0 * math.sin(a) - 0.25, 13.4 + 2.0 * math.sin(a) + 0.25)
               for a in [i * math.pi / 4 for i in range(8)])
    m += box(2.4, 3.6, -2.0, -0.4, 10.4, 16.4)                                       # lever
    for x in (-PEG_X, PEG_X):
        m += _diamond_x_axis(PEG_D, -0.5, PEG_LEN, x, PEG_Z)
    return m.transform(painting_frame())


def painting_plaque() -> Manifold:
    """The Cyber-Lich: framed portrait of a crowned, wired-up skull. Separate part:
    two holes in its back fit the pegs on the wall."""
    w, z0, z1, t = PAINT_W, PAINT_Z0, PAINT_Z1, 2.4
    h = z1 - z0
    zc = (z0 + z1) / 2
    m = box(-w / 2, w / 2, 0.15, t, z0, z1)
    m += box(-w / 2, w / 2, t, t + 0.8, z0, z1) - box(-w / 2 + 2, w / 2 - 2, t - 1, t + 1, z0 + 2, z1 - 2)
    face = lambda cs, a, b: extrude_xz(cs, t + a, t + b)
    skull = section([(6.0 * math.cos(q), zc + 1.0 + 6.0 * math.sin(q) * 1.05) for q in
                     [2 * math.pi * i / 40 for i in range(40)]])
    jaw = section([(-4.0, zc - 7.0), (4.0, zc - 7.0), (4.6, zc - 3.0), (-4.6, zc - 3.0)])
    m += face(skull + jaw, 0, 0.7)
    for x in (-2.4, 2.4):
        m -= face(section(circle_pts(x, zc + 0.6, 1.5, 16)[:-1]), 0.25, 2)
        m += face(section(circle_pts(x, zc + 0.6, 0.5, 10)[:-1]), 0.2, 0.75)       # glowing pupils
    m -= face(section([(-0.8, zc - 2.2), (0.8, zc - 2.2), (0.0, zc - 0.6)]), 0.25, 2)
    for x in (-3.0, -1.5, 0.0, 1.5, 3.0):
        m -= face(section([(x - 0.3, zc - 6.4), (x + 0.3, zc - 6.4), (x + 0.3, zc - 3.6), (x - 0.3, zc - 3.6)]), 0.3, 2)
    crown = [(-6.0, zc + 6.0)]
    for i in range(5):
        x = -6.0 + 12.0 * (i + 0.5) / 5
        crown += [(x - 1.0, zc + 6.0), (x, zc + 9.2), (x + 1.0, zc + 6.0)]
    crown += [(6.0, zc + 6.0), (6.0, zc + 4.6), (-6.0, zc + 4.6)]
    m += face(section(crown), 0, 0.9)
    # Circuit traces from the skull out to the frame.
    for sgn in (-1, 1):
        tr = section([(sgn * 5.0, zc - 1.0), (sgn * 9.0, zc - 1.0), (sgn * 9.0, zc - 5.5), (sgn * 10.4, zc - 5.5),
                      (sgn * 10.4, zc - 4.7), (sgn * 9.8, zc - 4.7), (sgn * 9.8, zc - 0.2), (sgn * 5.0, zc - 0.2)])
        m += face(tr, 0, 0.5)
        m += face(section(circle_pts(sgn * 10.0, zc + 4.0, 0.9, 12)[:-1]), 0, 0.5)
    for x in (-PEG_X, PEG_X):
        m -= _diamond_x_axis(PEG_HOLE, -1, PEG_LEN + 0.4, x, PEG_Z)
    return m.transform(painting_frame())


def painting_up() -> tuple[float, float, float]:
    T = painting_frame()
    return (float(T[0, 1]), float(T[1, 1]), 0.0)


# ---------------------------------------------------------------------------
# Everything
# ---------------------------------------------------------------------------


def guest_closet() -> Manifold:
    """Open-fronted closet against the wall (back at -Y): boxes | shelves | tuxedo."""
    w, d, h = 72.0, 15.0, 22.0
    m = box(-w / 2, w / 2, -d / 2 + 0.5, -d / 2 + 2.0, 0, h)          # back panel, clear of the seam
    for x in (-w / 2, -12.8, 11.2, w / 2 - 1.6):
        m += box(x, x + 1.6, -d / 2, d / 2, 0, h)
    m += box(-w / 2, w / 2, -d / 2, d / 2, 0, 1.0)
    for z in (8.0, 15.0):
        m += box(-12.0, 12.0, -d / 2, d / 2, z - 1.2, z)          # into the dividers
    m += P.box_stack([(-29, -1, 11, 11, 7, 0), (-18.5, 0, 9, 12, 6, 0), (-28.5, -1.5, 10, 9, 6, 8),
                      (-19, 0.5, 8, 8, 5, -6), (-24, -1, 9, 10, 4.5, 4)], seed=1).translate((0, 0, 1.0))
    m += P.pot(3.2, 3.0).translate((-5, 0, 0.95)) + P.pot(2.6, 2.4).translate((-5, 0, 3.95))
    m += P.pot(3.0, 4.0).rotate((0, 0, 180)).translate((5, -1, 0.95))
    m += P.books(8, -10.5, -1.0, 7.95, seed=2, depth=7)
    m += P.books(5, -10.5, -1.0, 14.95, seed=9, depth=7) + P.crate(7, 7, 4, False).translate((6, -1, 14.95))
    m += box(12.0, w / 2 - 0.8, -0.6, 0.6, 19.2, 20.4)                    # hanging rail
    m += tuxedo().translate((23.6, -d / 2 + 2.0, 0))
    return m


def build_props() -> Manifold:
    out = []
    add = out.append

    # --- corridor, lift, stairs ------------------------------------------------
    add(mount(neighbour_door(), "corr_n", 270, 195, (270, 230)))
    add(mount(call_panel(), "corr_s", 151, 260, (151, 230)))
    add(mount(handrail(64), "lifts_s", 110, 345, (110, 300)))
    add(mount(handrail(70), "lifts_w", 70, 302, (110, 302)))
    add(stair_flight())

    # --- hallway --------------------------------------------------------------------
    add(place(P.console_table(40, 8, 10), 355, 267, "s"))
    add(place(P.box_stack([(0, 0, 12, 10, 8, 0), (13, 1, 10, 10, 10, 8), (1, 1, 9, 8, 6, -10),
                           (6, -12, 14, 9, 5, 4)], seed=2), 246, 290))
    add(place(P.doormat(30, 10), 271, 270))
    add(place(P.plant(5.0, 7.0, 8, 13.0, seed=3), 467, 356))

    # --- gym ----------------------------------------------------------------------------
    add(place(P.boxing_ring(76.0), 398, 160))
    add(place(P.weight_rack(44, 10), 318, 205, "e"))
    add(place(P.plate_tree(), 330, 126))
    add(place(P.heavy_bag(), 456, 128))
    add(place(P.flat_bench(28), 345, 243, "e"))

    # --- shower, hot tub, spa -----------------------------------------------------
    for x in (498, 526):
        add(mount(shower_head(), "spa_n", x, 100, (x, 150)))
    add(place(P.sauna_bench(36, 8, 6), 485, 150, "e"))
    add(hot_tub())
    add(place(P.lounger(30, 12), 641, 324.5, 0))
    add(place(P.lounger(30, 12), 667, 324.5, 0))
    add(place(P.round_table(4.0, 7.0) + P.glass().translate((-1.2, 0, 7)) + P.glass().translate((1.6, 0.8, 7)),
              628, 330))
    add(place(P.sauna_bench(20, 8, 6) + P.towels(3).translate((-4.5, 0, 6)) + P.towels(2).translate((5, 0, 6)),
              733, 335, "n"))
    add(place(P.plant(5.0, 7.0, 7, 12.0, seed=4), 492, 330))
    add(place(P.plant(5.5, 8.0, 9, 14.0, seed=8), 705, 266))

    # --- sauna --------------------------------------------------------------------------
    add(place(P.sauna_bench(122, 11.5, 11), 808.75, 274, "w"))
    add(place(P.sauna_bench(122, 11.0, 6), 797.5, 274, "w"))
    add(place(P.sauna_bench(46, 10, 7), 717.5, 137, "s"))
    add(place(P.sauna_bench(70, 10, 7), 658, 167, "e"))
    add(place(P.sauna_stove(13), 770, 322))
    add(place(P.bucket(), 760, 300))

    # --- sensory deprivation chamber ----------------------------------------------
    add(place(P.float_pod(64, 26, 10), 725, 400))
    add(place(P.control_panel(), 768, 383, "w"))
    toward = (725, 400)
    for name, (x, y), a, b, skip in (("spa_s", (724, 343), (654.5, 343), (794.5, 343), ()),
                                    ("holo_n", (724, 455), (654.5, 455), (794.5, 455), ()),
                                    ("sdc_e", (797, 400), (797, 345.5), (797, 452.5), ()),
                                    ("sdc_w", (652, 400), (652, 345.5), (652, 452.5), ((403, 439),))):
        xa, xb = sorted((along(name, x, y, toward, a), along(name, x, y, toward, b)))
        sk = [tuple(sorted((along(name, x, y, toward, (652, s0)), along(name, x, y, toward, (652, s1)))))
              for s0, s1 in skip]
        add(mount(padding(xa, xb, sk), name, x, y, toward))
    add(mount(lock_button(), "sdc_w", 652, 396, (620, 396)))

    # --- WC, bath by the chamber, passage ----------------------------------------------
    add(place(P.toilet(), 601, 391, "n"))
    add(place(P.vanity(8, 6, 9), 586, 365, "e"))
    add(place(P.shower_tray(22, 32), 637, 365))
    add(mount(shower_head(), "spa_s", 637, 343, (637, 370)))
    add(place(P.vanity(16, 9, 9), 615, 448, "n"))

    # --- kitchen ------------------------------------------------------------------------
    add(place(P.counter(156, 13, 10, sink_x=40, hob_x=-30), 391, 376, "s"))
    add(mount(P.screen(14, 7).translate((0, 0, 18)), "kitchen_n", 391, 367, (391, 400)))
    add(place(P.fridge(16, 14, 22), 242, 440, "e"))
    add(place(P.chest_freezer(22, 12, 9), 241, 466, "e"))
    add(place(P.counter(56, 14, 10, doors=4), 385, 423, "s"))
    for x in (366, 385, 404):
        add(place(P.stool(), x, 443))
    add(place(P.pot(2.6, 2.4), 421 + 3.5, 376 - 2.6, z=10.4))

    # --- guest room ---------------------------------------------------------------------
    add(place(guest_closet(), 124, 356, "s"))
    add(place(P.bed(24, 42, 7, 14, 1), 95, 462, "e"))
    add(place(P.nightstand(), 79, 437, "e"))
    add(place(P.dresser(34, 10, 11), 190, 491, "n"))

    # --- master bath, closet ------------------------------------------------------------
    add(place(P.bathtub(52, 16, 7), 296, 495, "s"))
    add(place(P.toilet(), 242.5, 512, "e"))          # clear of the tile seam
    add(place(P.vanity(14, 8, 9), 321, 525, "w"))
    add(place(P.clothes_rack(38), 301.3, 546, "s"))
    add(place(P.backpack(), 300, 561, "n"))

    # --- master bedroom -----------------------------------------------------------------
    add(place(P.bed(50, 56, 8, 16), 120, 532, "s"))
    for x in (84, 156):
        add(place(P.nightstand(), x, 508.5, "s"))
    add(place(P.incense(), 156, 509, z=9.0))
    add(place(P.bottle(), 82, 509, z=9.0))
    add(mount(wall_safe(), "bed_n", 196, 500, (196, 560)))
    add(mount(acoustic_panels(-27, 27), "bed_n", 46, 500, (46, 560)))
    add(mount(acoustic_panels(-15, 15), "guest_e", 232, 521, (200, 521)))
    add(place(P.rug(46, 24), 120, 604))
    add(place(P.armchair(), 62, 612, 45))

    # --- storage --------------------------------------------------------------------------
    add(place(P.box_stack([(0, 0, 12, 12, 9, 0), (0, 14, 12, 12, 11, 0), (0, 28, 11, 12, 8, 0),
                           (0, 1, 10, 10, 7, 6), (0, 28, 9, 9, 6, -8), (1, 43, 12, 12, 10, 0)], seed=3),
              255, 630, "s"))
    for y in (640, 669):
        su = P.shelf_unit(26, 9, 22)
        su += P.crate(7, 6, 5, False).translate((-6, 0.5, 1.2)) + P.crate(6, 6, 4).translate((5, 0.5, 7.5))
        su += P.crate(9, 6, 5).translate((0, 0.5, 15.0))
        add(place(su, 320.5, y, "w"))
    add(place(P.box_stack([(0, 0, 13, 13, 10, 0), (2, 0, 9, 9, 7, 10), (-13, 4, 10, 10, 6, 5)], seed=4),
              293, 730, 20))

    # --- dining room ----------------------------------------------------------------------
    add(place(P.pedestal_table(120, 36, 11), 480, 560))
    for x in (435, 465, 495, 525):
        add(place(P.chair(), x, 537, "s"))
        add(place(P.chair(), x, 583, "n"))
    add(place(P.chair(), 415, 560, "e"))
    add(place(P.chair(), 545, 560, "w"))
    add(place(P.oysters(6.0), 446, 560, z=11))
    add(place(P.burgers(6.0), 474, 558, z=11))
    add(place(P.hotdogs(), 500, 561, z=11))
    for x in (435, 465, 495, 525):
        if not 440 < x < 506:                       # keep plates clear of the platters
            for y in (546, 574):
                add(place(P.plate(), x, y, z=11))
        add(place(P.glass(), x + 5, 547.5, z=11))
        add(place(P.glass(), x - 5, 572.5, z=11))
    add(place(P.plate(), 527, 560, z=11) + place(P.plate(), 433, 548, z=11))
    add(place(P.drinks_cabinet(40, 9, 10), 335.5, 515, "e"))
    add(cage())
    add(place(P.bowl(5.0), 360, 660))
    add(place(P.bone(9), 420, 667, 30))
    add(place(P.bone(7), 446, 648, -50))

    # --- holo space -------------------------------------------------------------------------
    add(place(P.pedestal_table(34, 20, 6, top=1.4, flare=3.0), 700, 545))
    add(place(P.cans(6), 692, 545, z=6))
    add(place(P.cans(3), 708, 551, z=6))
    add(place(P.glass(), 706, 540, z=6) + place(P.glass(), 711, 541, z=6))
    add(place(P.sofa(44, 13), 700, 516, "s"))
    add(place(P.sofa(34, 13), 742, 545, "w"))
    add(place(P.sofa(34, 13), 658, 545, "e"))
    add(place(P.armchair(), 700, 578, "n"))
    for (x, y) in ((620, 470), (775, 470), (735, 612)):
        add(place(P.holo_emitter(), x, y))
    add(place(P.drinks_cabinet(40, 9, 10), 720, 462.5, "s"))
    add(safe_and_pegs())

    # --- balcony ----------------------------------------------------------------------------
    add(place(P.sofa(30, 12), 420, 716, "s"))
    add(place(P.plant(5.5, 8.0, 8, 13.0, seed=6), 355, 721))
    add(place(P.plant(5.0, 7.0, 7, 12.0, seed=7), 625, 668))

    return union(out)


def floor_cuts() -> Manifold:
    """Extra grooves cut into the floor: shower drain, the balcony's weak section."""
    drain = section(circle_pts(*M(511, 152), 3.0, 24)[:-1])
    drain = drain - drain.offset(-GROOVE_W)
    m = extrude_xy(drain, FLOOR_T - GROOVE_D, FLOOR_T + 1)
    m += weak_floor()
    return m


def wall_cuts() -> Manifold:
    return safe_niche_cut()
