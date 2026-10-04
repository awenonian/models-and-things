"""Floor slab, floor finishes, walls and doorways of the penthouse.

Everything is built in model coordinates (see plan.M). Heights:
the floor slab is FLOOR_T thick, so models stand at z = FLOOR_T, and walls
are cut off WALL_H above that -- low enough to reach over, tall enough to
carry detail.
"""

from __future__ import annotations

import math
import random

import numpy as np
from manifold3d import CrossSection, JoinType, Manifold, OpType

from modelkit.csg import box, cyl, extrude_xy, section, union
from projects.reaper_vip import plan
from projects.reaper_vip.plan import M

FLOOR_T = 3.0
WALL_H = 25.0
TOP = FLOOR_T + WALL_H

GROOVE_W, GROOVE_D = 0.8, 0.6

# Glass walls: a sill, a thin pane, mullions and a head rail.
SILL_H = 5.0
PANE_T = 1.6
MULLION_W = 3.0
MULLION_GAP = 26.0          # max clear span of the head rail between mullions
RAIL_H = 14.0               # balcony rail height
RAIL_POST_GAP = 24.0


# ---------------------------------------------------------------------------
# Polylines
# ---------------------------------------------------------------------------


def smooth(pts, n: int = 8):
    """Catmull-Rom spline through the points (ends kept)."""
    p = [np.asarray(q, float) for q in pts]
    p = [2 * p[0] - p[1]] + p + [2 * p[-1] - p[-2]]
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(p[-2])
    return [tuple(map(float, q)) for q in out]


def wall_path(w: plan.Wall):
    """The wall's centre line in model coordinates."""
    pts = smooth(w.pts) if w.curve else w.pts
    return [M(*q) for q in pts]


def seg_rect(a, b, t: float, ext0: float, ext1: float) -> CrossSection:
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    L = float(np.linalg.norm(d))
    if L < 1e-9:
        return CrossSection()
    u = d / L
    n = np.array([-u[1], u[0]]) * t / 2
    a2, b2 = a - u * ext0, b + u * ext1
    return section([tuple(a2 + n), tuple(b2 + n), tuple(b2 - n), tuple(a2 - n)])


def stroke(path, t: float, cap: bool = True) -> CrossSection:
    """Band of width t along a polyline (square caps, joints filled)."""
    parts = []
    for i in range(len(path) - 1):
        e0 = t / 2 if (cap or i > 0) else 0.0
        e1 = t / 2 if (cap or i < len(path) - 2) else 0.0
        parts.append(seg_rect(path[i], path[i + 1], t, e0, e1))
    return CrossSection.batch_boolean(parts, OpType.Add)


def path_length(path) -> float:
    return sum(math.dist(path[i], path[i + 1]) for i in range(len(path) - 1))


def point_at(path, s: float):
    """(point, unit tangent) at arc length s along a polyline."""
    for i in range(len(path) - 1):
        L = math.dist(path[i], path[i + 1])
        if s <= L or i == len(path) - 2:
            a, b = np.asarray(path[i]), np.asarray(path[i + 1])
            u = (b - a) / max(L, 1e-9)
            return tuple(a + u * min(s, L)), tuple(u)
        s -= L
    raise ValueError


def nearest_on_walls(p, walls=None):
    """Closest wall segment to a model point: (wall, foot point, tangent, distance)."""
    best = None
    for w in walls or plan.WALLS:
        path = wall_path(w)
        for i in range(len(path) - 1):
            a, b = np.asarray(path[i]), np.asarray(path[i + 1])
            d = b - a
            L2 = float(d @ d)
            if L2 < 1e-12:
                continue
            s = float(np.clip((np.asarray(p) - a) @ d / L2, 0, 1))
            f = a + d * s
            dist = float(np.linalg.norm(np.asarray(p) - f))
            if best is None or dist < best[3]:
                best = (w, tuple(f), tuple(d / math.sqrt(L2)), dist)
    return best


def oriented_box(c, u, along: float, across: float, z0: float, z1: float) -> Manifold:
    """Box centred on plan point c, long axis along unit vector u."""
    ang = math.degrees(math.atan2(u[1], u[0]))
    return (box(-along / 2, along / 2, -across / 2, across / 2, z0, z1)
            .rotate((0, 0, ang)).translate((c[0], c[1], 0)))


# ---------------------------------------------------------------------------
# Floor
# ---------------------------------------------------------------------------


def outline_pts():
    """Outer wall centre lines, round the whole flat (map coords)."""
    pts = list(plan.OUTLINE_STRAIGHT_N) + [(797, 470)]
    pts += smooth(plan.OUTER_CURVE)[1:]
    storage = next(w for w in plan.WALLS if w.name == "storage_curve").pts
    pts += list(reversed(smooth(storage)))[1:]
    pts += [(185, 680)]
    pts += list(reversed(smooth(plan.BEDROOM_CURVE)))
    pts += [(70, 500), (70, 260), (66.5, 260)]
    return pts


def floor_plan() -> CrossSection:
    cs = section([M(*q) for q in outline_pts()]).offset(plan.T_EXT / 2, JoinType.Miter, 2.0)
    # The corridor runs on past the west end of the map: leave it open there.
    return cs - section([M(-100, 100), M(66.5, 100), M(66.5, 300), M(-100, 300)])


def _lines(bounds, pitch: float, angle: float, width: float = GROOVE_W, offset: float = 0.0):
    """Parallel grooves (as a CrossSection) covering bounds, rotated by angle."""
    x0, y0, x1, y1 = bounds
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = math.hypot(x1 - x0, y1 - y0) / 2 + pitch
    rects = []
    k = -math.ceil(r / pitch)
    while k * pitch <= r:
        y = k * pitch + offset
        rects.append(section([(-r, y - width / 2), (r, y - width / 2), (r, y + width / 2),
                              (-r, y + width / 2)]))
        k += 1
    cs = CrossSection.batch_boolean(rects, OpType.Add)
    return cs.rotate(angle).translate((cx, cy))


def _planks(bounds, pitch: float, angle: float, joint: float = 64.0, seed: int = 3):
    """Plank grooves plus staggered butt joints."""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = bounds
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = math.hypot(x1 - x0, y1 - y0) / 2 + pitch
    parts = [_lines((-r, -r, r, r), pitch, 0)]
    k = -math.ceil(r / pitch)
    while k * pitch <= r:
        ya, yb = k * pitch, (k + 1) * pitch
        x = -r + rnd.uniform(0, joint)
        while x < r:
            parts.append(section([(x - GROOVE_W / 2, ya), (x + GROOVE_W / 2, ya),
                                  (x + GROOVE_W / 2, yb), (x - GROOVE_W / 2, yb)]))
            x += joint
        k += 1
    cs = CrossSection.batch_boolean(parts, OpType.Add)
    return cs.rotate(angle).translate((cx, cy))


def _hexes(bounds, size: float):
    x0, y0, x1, y1 = bounds
    w = math.sqrt(3) * size
    cells = []
    row = 0
    y = y0 - size
    while y < y1 + size:
        x = x0 - w + (w / 2 if row % 2 else 0)
        while x < x1 + w:
            hexa = [(x + size * math.cos(math.radians(30 + 60 * i)),
                     y + size * math.sin(math.radians(30 + 60 * i))) for i in range(6)]
            c = section(hexa)
            cells.append(c - c.offset(-GROOVE_W, JoinType.Miter, 2.0))
            x += w
        y += 1.5 * size
        row += 1
    return CrossSection.batch_boolean(cells, OpType.Add)


def _pavers(bounds, pitch: float, angle: float):
    """Staggered stone pavers (rows of pitch, joints offset by half)."""
    x0, y0, x1, y1 = bounds
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = math.hypot(x1 - x0, y1 - y0) / 2 + pitch
    parts = [_lines((-r, -r, r, r), pitch, 0)]
    k = -math.ceil(r / pitch)
    while k * pitch <= r:
        ya, yb = k * pitch, (k + 1) * pitch
        x = -r + (pitch * 0.75 if k % 2 else 0)
        while x < r:
            parts.append(section([(x - GROOVE_W / 2, ya), (x + GROOVE_W / 2, ya),
                                  (x + GROOVE_W / 2, yb), (x - GROOVE_W / 2, yb)]))
            x += pitch * 1.5
        k += 1
    return CrossSection.batch_boolean(parts, OpType.Add).rotate(angle).translate((cx, cy))


def floor_pattern(room: plan.Room) -> CrossSection:
    region = section([M(*q) for q in room.poly])
    b = region.bounds()
    p, a = room.pitch, room.angle
    if room.floor in ("tiles", "small_tiles", "rubber"):
        w = 1.0 if room.floor == "rubber" else GROOVE_W
        g = _lines(b, p, a, w) + _lines(b, p, a + 90, w)
    elif room.floor in ("plate", "quilt"):
        g = _lines(b, p, 45 + a) + _lines(b, p, -45 + a)
    elif room.floor == "planks":
        g = _planks(b, p, a, seed=hash(room.name) % 97)
    elif room.floor in ("slats", "deck"):
        g = _lines(b, p, a)
    elif room.floor == "stone":
        g = _pavers(b, p, a)
    elif room.floor == "hex":
        g = _hexes(b, p)
    else:
        return CrossSection()
    return g ^ region


# ---------------------------------------------------------------------------
# Walls
# ---------------------------------------------------------------------------


def build_wall(w: plan.Wall) -> Manifold:
    path = wall_path(w)
    if w.kind == "solid":
        return extrude_xy(stroke(path, w.t), 0.0, TOP)
    if w.kind == "rail":
        top = FLOOR_T + RAIL_H
        m = extrude_xy(stroke(path, w.t), 0.0, FLOOR_T + 1.5)          # kick plate
        m += extrude_xy(stroke(path, PANE_T), 0.0, top)                  # glass
        m += _chamfered_rail(path, w.t, top - 1.0, top)                  # handrail
        m += _posts(path, w.t, RAIL_POST_GAP, top)
        return m
    sill = SILL_H if w.kind == "glass" else 1.0
    m = extrude_xy(stroke(path, w.t), 0.0, FLOOR_T + sill)
    m += extrude_xy(stroke(path, PANE_T), 0.0, TOP)
    m += _chamfered_rail(path, w.t, TOP - 1.5, TOP)                       # head rail
    m += _posts(path, w.t, MULLION_GAP, TOP, corners=not w.curve)
    return m


def _chamfered_rail(path, t: float, z_flat: float, top: float) -> Manifold:
    """Rail as wide as the wall sitting on the thin pane, with a stepped 45-degree
    underside so it prints without support. Full width from z_flat to top."""
    # Each step runs all the way up to `top`, so neighbouring steps overlap instead
    # of meeting face to face (which can leave zero-thickness sheets in the mesh).
    layers = [extrude_xy(stroke(path, t), z_flat, top)]
    steps = max(1, math.ceil((t - PANE_T) / 2 / 0.45))
    dz = (t - PANE_T) / 2 / steps
    for k in range(steps):
        wk = PANE_T + (t - PANE_T) * (k + 1) / steps
        layers.append(extrude_xy(stroke(path, wk), z_flat - (steps - k) * dz, top))
    return union(layers)


def _posts(path, t: float, gap: float, top: float, corners: bool = True) -> Manifold:
    """Mullions/posts: at both ends, at corners, and so no clear span exceeds `gap`."""
    posts = []
    L = path_length(path)
    stops = [0.0]
    if corners:
        acc = 0.0
        for i in range(1, len(path) - 1):
            acc += math.dist(path[i - 1], path[i])
            stops.append(acc)
    stops.append(L)
    ss = []
    for a, b in zip(stops[:-1], stops[1:]):
        n = max(1, math.ceil((b - a) / (gap + MULLION_W)))
        ss += [a + (b - a) * k / n for k in range(n)]
    ss.append(L)
    for s in ss:
        p, u = point_at(path, s)
        posts.append(oriented_box(p, u, MULLION_W, t, 0.0, top))
    return union(posts)


def door_cut(d: plan.Door):
    """(cut solid, jamb solid) for a doorway."""
    c = M(d.x, d.y)
    w, foot, u, dist = nearest_on_walls(c)
    assert dist < 3.0, f"door at {d.x},{d.y} is {dist:.1f} mm off any wall"
    cut = oriented_box(foot, u, d.w, w.t + 3.0, FLOOR_T, TOP + 1)
    jambs = []
    un = np.asarray(u)
    for sgn in (-1, 1):
        if w.kind == "solid" and d.jambs:
            p = np.asarray(foot) + un * sgn * (d.w / 2 + 0.8)
            jambs.append(oriented_box(tuple(p), u, 1.6, w.t + 1.6, 0.0, TOP))
        elif w.kind != "solid":
            p = np.asarray(foot) + un * sgn * (d.w / 2 + MULLION_W / 2)
            top = FLOOR_T + RAIL_H if w.kind == "rail" else TOP
            jambs.append(oriented_box(tuple(p), u, MULLION_W, w.t, 0.0, top))
    return cut, union(jambs)


def build_shell(extra_cuts: Manifold | None = None) -> tuple[Manifold, Manifold]:
    """(floor with finishes, walls with doorways)."""
    floor_cs = floor_plan()
    floor = extrude_xy(floor_cs, 0.0, FLOOR_T)
    inner = floor_cs.offset(-1.0, JoinType.Miter, 2.0)
    grooves = CrossSection.batch_boolean([floor_pattern(r) for r in plan.ROOMS], OpType.Add) ^ inner
    floor -= extrude_xy(grooves, FLOOR_T - GROOVE_D, FLOOR_T + 1)

    walls = union(build_wall(w) for w in plan.WALLS)
    walls += union(cyl(r, 0.0, TOP, *M(x, y), segments=40) for x, y, r in plan.PIERS)
    cuts, jambs = zip(*(door_cut(d) for d in plan.DOORS))
    walls -= union(cuts)
    walls += union(jambs)
    # Nothing outside the slab (wall caps at the open corridor end, etc.).
    walls ^= extrude_xy(floor_cs, -1, TOP + 1)
    return floor, walls
