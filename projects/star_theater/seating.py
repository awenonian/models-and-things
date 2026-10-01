"""The Star Theater -- seating piece (part two).

The house side of Colette Du Bois' theater, built to face the stage piece
across the table: eight curved, raked rows of velvet chairs with a cross aisle
in front, a centre aisle and side aisles, a tiled promenade at the back, and
over the promenade a small balcony on cast-iron columns, against the
auditorium's back wall.

Run from the repo root:
    python -m projects.star_theater.seating

Outputs (in projects/star_theater/output/):
    seating_assembled.stl   the whole piece as it stands on the table (preview)
    print/seating_*.stl     printable parts, already rotated into print orientation

Coordinates follow the stage piece: +Y points away from the stage, so this
piece's front edge (the pit) is at y = 0 and its back wall at the far end.
Left/right are as seen from the audience (+x is the audience's left).

The rows are close-packed (17 mm pitch): models stand on the chairs, which
count as difficult terrain that gives cover. The aisles stay wide (44 mm centre,
32 mm sides) as the fast way forward. The balcony is a separate part resting on
BBs, so it lifts off if you leave it unglued.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from manifold3d import CrossSection, Manifold

from modelkit.csg import (
    ball_pocket, box, circle_pts, cyl, extrude_xy, extrude_xz, extrude_yz, ring,
    section, sphere, star_pts, text_section, union,
)
from modelkit.export import export_parts
from projects.star_theater.ornament import pilaster

OUT_DIR = Path(__file__).parent / "output"

# ---------------------------------------------------------------------------
# Key dimensions (mm)
# ---------------------------------------------------------------------------

HALF_W = 200.0
FLOOR = 8.0             # front cross-aisle floor (the base plate thickness)
RISE = 3.0              # each row steps up this much
N_ROWS = 8
ROW_D = 17.0            # row pitch: chairs are 12 mm deep, ~5 mm between rows
CENTER_Y = -900.0       # rows are arcs centred here, i.e. behind the stage
ROW1_R = 950.0          # front edge of row 1 (y = 50 on the centre line)
PROM_R = ROW1_R + N_ROWS * ROW_D
PROM_Z = FLOOR + N_ROWS * RISE
WALL_T = 12.0
WALL_Y = 240.0          # front face of the back wall
BACK_Y = WALL_Y + WALL_T
WALL_H = 123.0          # wall body height above the promenade
AISLE_HW = 22.0         # centre aisle half-width
SIDE_AISLE_X = 168.0    # side aisles run from here to the edge
SEAT_PITCH = 11.0

# Balcony: over the promenade, resting on four columns and a wall ledge.
BAL_HW = 105.0
BAL_UNDER = PROM_Z + 52.0          # underside (52 mm of headroom below)
BAL_SLAB = 8.0
BAL_FLOOR = BAL_UNDER + BAL_SLAB   # front-row floor
BAL_STEP = 6.0                     # second row is raised this much
BAL_DEPTH = 46.0                   # wall to the balcony's front at its ends
BAL_BOW = 8.0                      # extra bulge at the centre
BAL_AISLE_HW = 16.0
COLUMN_X = (45.0, 95.0)

# Print layout: base split down the centre aisle and along the front edge of
# row 5 (the seam hides at the foot of a riser); wall split beside the centre
# pilasters; balcony printed flat as one part. Joinery as on the stage: steel
# BB pockets + wall tenon in a slot.
SEAM_R = ROW1_R + 4 * ROW_D
WALL_SEAM_X = 42.0
TENON = 2.0
SLOT_CLEAR = 0.2

DOOR_C_HW, DOOR_C_SPRING = 18.0, 26.0     # centre double door: 36 x 44
DOOR_S_X, DOOR_S_HW, DOOR_S_SPRING = 182.0, 15.0, 35.0   # side doors: 30 x 50
DOOR_B_HW = 15.0                          # balcony door: 30 x 45
PILASTERS = ((32.0, 6.0), (111.0, 5.0))   # (x, half-width), mirrored


def mirror_x(m: Manifold) -> Manifold:
    return m.mirror((1, 0, 0))


def both_sides(m: Manifold) -> Manifold:
    return m + mirror_x(m)


# ---------------------------------------------------------------------------
# Plan geometry: arcs about (0, CENTER_Y)
# ---------------------------------------------------------------------------


def arc_y(r: float, x: float) -> float:
    return CENTER_Y + math.sqrt(r * r - x * x)


def arc_pts(r: float, x0: float = -HALF_W, x1: float = HALF_W, n: int = 120):
    return [(x0 + (x1 - x0) * i / n, arc_y(r, x0 + (x1 - x0) * i / n)) for i in range(n + 1)]


def beyond(r: float, y_max: float = BACK_Y) -> CrossSection:
    """Plan region of the base farther from the stage than radius r."""
    return section(arc_pts(r) + [(HALF_W, y_max), (-HALF_W, y_max)])


def band(r0: float, r1: float, x0: float = -HALF_W, x1: float = HALF_W) -> CrossSection:
    return section(arc_pts(r0, x0, x1) + list(reversed(arc_pts(r1, x0, x1))))


def base_plan() -> CrossSection:
    return section([(-HALF_W, 0), (HALF_W, 0), (HALF_W, BACK_Y), (-HALF_W, BACK_Y)])


def row_r(k: int) -> float:
    """Front-edge radius of row k (1-based); k = N_ROWS + 1 is the promenade."""
    return ROW1_R + (k - 1) * ROW_D


def row_z(k: int) -> float:
    return FLOOR + (k - 1) * RISE


def polar(r: float, theta: float) -> tuple[float, float]:
    return (r * math.sin(theta), CENTER_Y + r * math.cos(theta))


# ---------------------------------------------------------------------------
# The house floor: base, raked rows, aisles
# ---------------------------------------------------------------------------


def build_floor() -> Manifold:
    plan = base_plan()
    m = extrude_xy(plan, 0, FLOOR)
    for k in range(2, N_ROWS + 2):
        m += extrude_xy(beyond(row_r(k)), row_z(k - 1), row_z(k))
    # Brass nosing along each riser (0.8 mm lip: prints fine).
    for k in range(2, N_ROWS + 2):
        m += extrude_xy(band(row_r(k) - 0.8, row_r(k) + 1.5), row_z(k) - 0.8, row_z(k))
    m -= floor_grooves()
    m += carpet_runner()
    for k in range(1, N_ROWS + 1):
        m += chair_row(k)
    for x in COLUMN_X:
        for sx in (-1, 1):
            m += column(sx * x)
    return m


def floor_grooves() -> Manifold:
    """A diamond-tiled promenade (and the cross aisle in front of row 1)."""
    cuts = []
    # Promenade tiles: two families of 45-degree grooves.
    tiles = []
    step = 14.0
    for k in range(-40, 40):
        for sgn in (1, -1):
            g = box(-300, 300, -0.4, 0.4, PROM_Z - 0.6, PROM_Z + 1).rotate((0, 0, 45 * sgn))
            tiles.append(g.translate((0, 200 + k * step, 0)))
    prom = beyond(row_r(N_ROWS + 1) + 3) ^ section([(-500, 0), (500, 0), (500, WALL_Y),
                                                     (-500, WALL_Y)])
    prom = prom.offset(-1.5) - section([(-17, 0), (17, 0), (17, 400), (-17, 400)])  # not under the runner
    cuts.append(union(tiles) ^ extrude_xy(prom, 0, 100))
    # Cross aisle: same tiles, at floor level.
    front = (base_plan() - beyond(ROW1_R - 3)).offset(-1.5) - section(
        [(-17, -10), (17, -10), (17, 400), (-17, 400)])
    front_tiles = union(t.translate((0, 0, FLOOR - PROM_Z)) for t in tiles)
    cuts.append(front_tiles ^ extrude_xy(front, 0, 100))
    return union(cuts)


def carpet_runner() -> Manifold:
    """A raised runner down the centre aisle, stepping with the rows."""
    parts = []
    strip = section([(-16, 0), (16, 0), (16, WALL_Y), (-16, WALL_Y)])
    for k in range(1, N_ROWS + 2):
        r0 = 0.0 if k == 1 else row_r(k) + 1.5
        r1 = row_r(k + 1) - 0.8 if k <= N_ROWS else 5000
        lo = base_plan() if k == 1 else beyond(r0)
        region = (lo - beyond(r1)) ^ strip if k <= N_ROWS else lo ^ strip
        parts.append(extrude_xy(region, row_z(k) - 0.1, row_z(k) + 0.5))
        parts.append(extrude_xy(ring(region, 0, -1.4), row_z(k) + 0.4, row_z(k) + 0.8))
    return union(parts)


# ---------------------------------------------------------------------------
# Chairs
# ---------------------------------------------------------------------------


def chair() -> Manifold:
    """A velvet theatre chair, facing -y, origin at the front centre of the seat
    on the floor. ~10 mm wide, 12 mm deep, 16 mm tall."""
    w = 4.6
    seat = box(-w, w, 0.6, 9.5, 0, 5.6)
    seat += box(-w + 0.3, w - 0.3, 0.2, 9.0, 5.6, 6.6)          # cushion
    back = box(-w, w, 9.0, 12.0, 0, 14.2)
    top = Manifold.cylinder(2 * w, 1.5, 1.5, 20, True).rotate((0, 90, 0)).translate((0, 10.5, 14.2))
    back += top
    # Tufting on the back.
    for x in (-1.8, 1.8):
        back -= box(x - 0.3, x + 0.3, 8.6, 9.3, 8.0, 13.5)
    back -= box(-w + 0.8, w - 0.8, 8.6, 9.3, 7.4, 7.9)
    # Armrest divider on one side (the neighbour supplies the other).
    arm = section([(1.0, 0), (12.0, 0), (12.0, 9.6), (2.0, 9.6), (1.0, 8.8)])
    divider = extrude_yz(arm, -5.5 - 0.6, -5.5 + 0.6)
    return seat + back + divider


def end_standard() -> Manifold:
    """Cast-iron aisle-end panel with a scroll top and a star, at x = 0."""
    prof = section([(0.6, 0), (12.6, 0), (12.6, 13.0), (10.5, 15.2), (8.6, 14.6), (6.0, 11.0),
                    (2.0, 11.0), (0.6, 9.6)])
    m = extrude_yz(prof, -0.9, 0.9)
    star = section(star_pts(6.5, 6.0, 2.6))
    for sx in (-1, 1):
        sm = Manifold.extrude(star, 0.5).transform([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]])
        m += sm.translate((0.9, 0, 0)) if sx > 0 else sm.translate((-1.4, 0, 0))
    return m


def chair_row(k: int) -> Manifold:
    """Row k: chairs against the back of the row, both blocks, curved."""
    r = row_r(k + 1) - 13.0                 # chair origin radius (back 1 mm off the riser)
    z = row_z(k)
    c, std = chair(), end_standard()
    parts = []
    for side in (1, -1):
        x_in, x_out = AISLE_HW + 2.5, SIDE_AISLE_X - 2.5
        t0, t1 = math.asin(x_in / r), math.asin(x_out / r)
        n = int((t1 - t0) * r // SEAT_PITCH)
        tc = (t0 + t1) / 2
        dt = SEAT_PITCH / r
        thetas = [tc + (i - (n - 1) / 2) * dt for i in range(n)]
        for t in thetas:
            x, y = polar(r, t)
            parts.append(c.rotate((0, 0, -math.degrees(t))).translate((x, y, z)))
        for t in (thetas[0] - dt / 2 - 0.9 / r, thetas[-1] + dt / 2 + 0.9 / r):
            x, y = polar(r, t)
            parts.append(std.rotate((0, 0, -math.degrees(t))).translate((x, y, z)))
        if side < 0:
            parts = parts[:-(n + 2)] + [mirror_x(p) for p in parts[-(n + 2):]]
    return union(parts)


# ---------------------------------------------------------------------------
# Back wall (built in the 'stage frame': face at y = 0 facing +y, then turned
# round to face the stage)
# ---------------------------------------------------------------------------


def _door(cx: float, hw: float, spring: float) -> CrossSection:
    pts = [(cx - hw, PROM_Z - 30), (cx + hw, PROM_Z - 30)]
    pts += circle_pts(cx, PROM_Z + spring, hw, 32, 0, 180)
    return section(pts)


def _above_prom() -> CrossSection:
    return section([(-500, PROM_Z), (500, PROM_Z), (500, 1000), (-500, 1000)])


def poster(cx: float, lines: list[tuple[str, float]], hw: float = 22.0) -> Manifold:
    """A framed playbill with lettering, in relief."""
    z0, z1 = PROM_Z + 30, PROM_Z + 88
    board = section([(cx - hw, z0), (cx + hw, z0), (cx + hw, z1), (cx - hw, z1)])
    m = extrude_xz(board, -0.1, 1.2)
    m += extrude_xz(ring(board, 2.0, 0), -0.1, 2.6)
    m += extrude_xz(ring(board, -1.6, -2.4), 1.0, 1.7)
    z = z1 - 7
    for text, h in lines:
        if text == "*":
            m += extrude_xz(section(star_pts(cx, z - 3, 4.5)), 1.0, 2.2)
            z -= 11
            continue
        cs = text_section(text, h, cx, z - h / 2, spacing=0.05, mirror=True)
        (x0, _, x1, _) = cs.bounds()
        if x1 - x0 > 2 * hw - 6:                     # squeeze long words to fit
            cs = cs.translate((-cx, 0)).scale(((2 * hw - 6) / (x1 - x0), 1)).translate((cx, 0))
        m += extrude_xz(cs, 1.0, 2.0)
        z -= h + 4
    return m


def sconce(cx: float, cz: float) -> Manifold:
    """Gas-lamp wall sconce, all in relief."""
    plate = section(circle_pts(cx, cz - 9, 2.6, 20))
    m = extrude_xz(plate, -0.1, 1.4)
    arm = section([(cx - 0.9, cz - 9), (cx + 0.9, cz - 9), (cx + 0.9, cz - 2), (cx - 0.9, cz - 2)])
    m += extrude_xz(arm, -0.1, 4.0)
    cup = section([(cx - 2.2, cz - 2.5), (cx + 2.2, cz - 2.5), (cx + 1.2, cz - 4), (cx - 1.2, cz - 4)])
    m += extrude_xz(cup, -0.1, 5.0)
    globe = (section(circle_pts(cx, cz + 1.2, 3.4, 24))
             + section([(cx - 1.6, cz - 2.6), (cx + 1.6, cz - 2.6), (cx + 1.6, cz), (cx - 1.6, cz)]))
    m += extrude_xz(globe, -0.1, 5.0)
    m += sphere(3.4, cx, 5.0, cz + 1.2, 20) ^ box(cx - 5, cx + 5, 5.0, 10, cz - 5, cz + 6)
    return m


def back_wall_local() -> Manifold:
    """The wall in the stage frame: face at y = 0 facing +y, back at y = -WALL_T."""
    top = PROM_Z + WALL_H
    w = box(-HALF_W, HALF_W, -WALL_T, 0, PROM_Z, top)
    w += box(-HALF_W, HALF_W, 0, 1.5, PROM_Z, PROM_Z + 6)                    # baseboard
    w += extrude_yz(section([(0, PROM_Z + 22), (2.2, PROM_Z + 23), (2.2, PROM_Z + 25),
                             (0, PROM_Z + 26.5)]), -HALF_W, HALF_W)            # dado rail
    # Cornice (back face stays flat: it prints face-down on the bed).
    z0 = top
    prof = section([(-WALL_T, z0), (1.5, z0), (1.5, z0 + 2.5), (3.0, z0 + 4.0), (5.5, z0 + 6.5),
                    (5.5, z0 + 8.0), (7.5, z0 + 10.0), (8.5, z0 + 10.0), (8.5, z0 + 13),
                    (-WALL_T, z0 + 13)])
    w += extrude_yz(prof, -HALF_W, HALF_W)
    x = -HALF_W + 2
    dent = []
    while x < HALF_W - 4:
        dent.append(box(x, x + 3, 0, 3.2, z0 - 3.5, z0 + 0.5))
        x += 6
    w += union(dent)
    clip = _above_prom()
    # Door surrounds.
    doors = [_door(0, DOOR_C_HW, DOOR_C_SPRING)] + [_door(sx * DOOR_S_X, DOOR_S_HW, DOOR_S_SPRING)
                                                    for sx in (-1, 1)]
    for d in doors:
        w += extrude_xz(ring(d, 4.5, 0) ^ clip, 0, 2.2)
        w += extrude_xz(ring(d, 3.0, 1.2) ^ clip, 0, 3.4)
    # Ledge carrying the back of the balcony (45-degree underside).
    w += extrude_yz(section([(0, BAL_UNDER - 12), (6, BAL_UNDER - 6), (6, BAL_UNDER),
                             (0, BAL_UNDER)]), -BAL_HW, BAL_HW)
    # Balcony door, opening off the balcony's back walkway.
    bz = BAL_FLOOR + BAL_STEP
    bdoor = section([(-DOOR_B_HW, bz), (DOOR_B_HW, bz)] + circle_pts(0, bz + 30, DOOR_B_HW, 32, 0, 180))
    bclip = section([(-500, bz), (500, bz), (500, 1000), (-500, 1000)])
    w += extrude_xz(ring(bdoor, 4.5, 0) ^ bclip, 0, 2.2)
    w += extrude_xz(ring(bdoor, 3.0, 1.2) ^ bclip, 0, 3.4)
    w += extrude_xz(section(star_pts(0, bz + 49, 4.0)), 0, 3.6)
    # Pilasters.
    for (x, hw) in PILASTERS:
        for sx in (-1, 1):
            w += pilaster(sx * x, PROM_Z, top, hw=hw)
    # Playbills (outside the balcony) and gas sconces (under it and above it).
    w += poster(-139.0, [("COLETTE", 7.0), ("DU BOIS", 5.0), ("*", 0), ("STAR OF", 4.2),
                         ("THE SHOW", 4.2)], hw=20.0)
    w += poster(139.0, [("THE", 4.2), ("MECHANICAL", 5.0), ("DOVES", 7.0), ("*", 0),
                        ("NIGHTLY", 4.2)], hw=20.0)
    for cx in (-70, 70):
        w += sconce(cx, PROM_Z + 34)
    for cx in (-50, 50):
        w += sconce(cx, bz + 30)
    # Cut the doorways, and trim anything poking past the wall ends.
    for d in doors:
        w -= extrude_xz(d ^ clip, -40, 40)
    w -= extrude_xz(bdoor, -40, 40)
    w ^= box(-HALF_W, HALF_W, -WALL_T, 50, 0, 500)
    # Tenon under the solid runs.
    runs = [(-HALF_W, -DOOR_S_X - DOOR_S_HW), (-DOOR_S_X + DOOR_S_HW, -DOOR_C_HW),
            (DOOR_C_HW, DOOR_S_X - DOOR_S_HW), (DOOR_S_X + DOOR_S_HW, HALF_W)]
    for a, b in runs:
        if b - a > 1:
            w += box(a, b, -WALL_T, 0, PROM_Z - TENON, PROM_Z + 0.01)
    return w


def to_world(m: Manifold) -> Manifold:
    """Turn a stage-frame wall round to face the stage, at the back of this piece."""
    return m.rotate((0, 0, 180)).translate((0, WALL_Y, 0))


def tenon_plan_world() -> CrossSection:
    tenon = to_world(back_wall_local()) ^ box(-500, 500, -500, 500, PROM_Z - TENON, PROM_Z - 0.5)
    return tenon.project()


# ---------------------------------------------------------------------------
# Balcony and its columns
# ---------------------------------------------------------------------------


def bal_front(x: float) -> float:
    """y of the balcony's bowed front edge."""
    return WALL_Y - BAL_DEPTH - BAL_BOW * (1 - (x / BAL_HW) ** 2)


def _bal_slope(x: float) -> float:
    return 2 * BAL_BOW * x / BAL_HW ** 2


def _behind_front(off: float, y_back: float = WALL_Y - 0.2, n: int = 60) -> CrossSection:
    xs = [-BAL_HW + 2 * BAL_HW * i / n for i in range(n + 1)]
    return section([(x, bal_front(x) + off) for x in xs] + [(BAL_HW, y_back), (-BAL_HW, y_back)])


def _front_band(inner: float, outer: float, n: int = 60) -> CrossSection:
    xs = [-BAL_HW + 2 * BAL_HW * i / n for i in range(n + 1)]
    return section([(x, bal_front(x) - outer) for x in xs]
                   + [(x, bal_front(x) + inner) for x in reversed(xs)])


def column_xy() -> list[tuple[float, float]]:
    return [(sx * x, bal_front(x) + 6.0) for x in COLUMN_X for sx in (-1, 1)]


def column(cx: float) -> Manifold:
    """Cast-iron column from the promenade up to the balcony's underside."""
    cy = bal_front(abs(cx)) + 6.0
    z0, z1 = PROM_Z, BAL_UNDER
    m = box(cx - 3.5, cx + 3.5, cy - 3.5, cy + 3.5, z0 - 0.1, z0 + 3)
    m += box(cx - 3.0, cx + 3.0, cy - 3.0, cy + 3.0, z0 + 3, z0 + 4)
    m += cyl(2.3, z0 + 4, z1 - 7, cx, cy, segments=24)
    m += cyl(2.8, z0 + 4, z0 + 5.2, cx, cy, segments=24)
    m += cyl(2.8, z1 - 9, z1 - 7.8, cx, cy, segments=24)
    # Capital: square flare at 45 degrees up to a 9 mm abacus.
    flare = (box(cx - 2.5, cx + 2.5, cy - 2.5, cy + 2.5, z1 - 7.1, z1 - 7) +
             box(cx - 4.5, cx + 4.5, cy - 4.5, cy + 4.5, z1 - 5.0, z1 - 4.9)).hull()
    m += flare + box(cx - 4.5, cx + 4.5, cy - 4.5, cy + 4.5, z1 - 5.0, z1)
    return m


def balcony() -> Manifold:
    """Two bowed rows of chairs over the promenade. Printed flat on its underside."""
    z0, z1 = BAL_UNDER, BAL_FLOOR
    zb = z1 + BAL_STEP
    m = extrude_xy(_behind_front(0), z0, z1)
    m += extrude_xy(_front_band(0, 0.8), z1 - 1.6, z1)                 # lip on the fascia
    m += extrude_xy(_behind_front(22), z1 - 0.1, zb)                    # raised back row
    m += extrude_xy(_behind_front(21.2) - _behind_front(23.5), zb - 0.8, zb)    # nosing
    # Stars along the fascia.
    for x in (-75, -45, -15, 15, 45, 75):
        y = bal_front(x)
        m += extrude_xz(section(star_pts(x, (z0 + z1) / 2 - 0.6, 2.8)), y - 1.0, y + 1.0)
    # Bowed parapet with posts, ball finials and stars.
    ph = 14.0
    m += extrude_xy(_front_band(3.0, 0.0), z1 - 0.1, z1 + ph)
    m += extrude_xy(_front_band(3.8, 0.8), z1 + ph, z1 + ph + 1.5)
    posts = [-BAL_HW + 2.5, -70, -35, 0, 35, 70, BAL_HW - 2.5]
    for x in posts:
        y = bal_front(x) + 1.5
        m += box(x - 2.4, x + 2.4, y - 2.4, y + 2.4, z1 - 0.1, z1 + ph + 2.5)
        m += sphere(2.0, x, y, z1 + ph + 4.0, 14)
    for a, b in zip(posts[:-1], posts[1:]):
        x = (a + b) / 2
        y = bal_front(x)
        m += extrude_xz(section(star_pts(x, z1 + ph / 2, 3.4)), y - 0.8, y + 1.0)
    # Side parapets.
    yb0, yb1 = bal_front(BAL_HW), WALL_Y - 0.2
    for sx in (-1, 1):
        xo, xi = sx * BAL_HW, sx * (BAL_HW - 3)
        m += box(xi, xo, yb0, yb1, z1 - 0.1, zb + ph)
        m += box(xi - sx * 0.8, xo + sx * 0.8, yb0, yb1, zb + ph, zb + ph + 1.5)
    # Chairs, following the bow, either side of the aisle.
    c, std = chair(), end_standard()
    for off, zr in ((5.0, z1), (24.0, zb)):
        half = []
        x_in, x_out = BAL_AISLE_HW + 1.5, BAL_HW - 4.5
        n = int((x_out - x_in) // SEAT_PITCH)
        xs = [(x_in + x_out) / 2 + (i - (n - 1) / 2) * SEAT_PITCH for i in range(n)]
        for x in xs:
            a = math.degrees(math.atan(_bal_slope(x)))
            half.append(c.rotate((0, 0, a)).translate((x, bal_front(x) + off, zr)))
        for x in (xs[0] - SEAT_PITCH / 2 - 0.9, xs[-1] + SEAT_PITCH / 2 + 0.9):
            a = math.degrees(math.atan(_bal_slope(x)))
            half.append(std.rotate((0, 0, a)).translate((x, bal_front(x) + off, zr)))
        h = union(half)
        m += h + mirror_x(h)
    # Clearance round the wall's pilasters, and BB pockets underneath.
    for (x, hw) in PILASTERS:
        for sx in (-1, 1):
            m -= box(sx * x - hw - 3.0, sx * x + hw + 3.0, WALL_Y - 8.0, WALL_Y + 1, 0, 500)
    for (x, y) in _bal_pocket_xy():
        m -= ball_pocket(x, y, z0)
    return m


def _bal_pocket_xy() -> list[tuple[float, float]]:
    return column_xy() + [(sx * x, WALL_Y - 3.0) for x in (20.0, 75.0) for sx in (-1, 1)]


# ---------------------------------------------------------------------------
# Joinery
# ---------------------------------------------------------------------------


def floor_pockets() -> Manifold:
    holes = [ball_pocket(0, y, 4.0) for y in (25, 95, 160, 220)]
    for x in (-150, -95, -45, 45, 95, 150):
        holes.append(ball_pocket(x, arc_y(SEAM_R, x), 4.0))
    return union(holes)


def wall_pockets_local() -> Manifold:
    # Balcony seats on the ledge (pockets in the ledge top; local frame).
    holes = [ball_pocket(-x, WALL_Y - y, BAL_UNDER) for (x, y) in _bal_pocket_xy()
             if y > WALL_Y - 5]
    for sx in (-1, 1):
        for z in (PROM_Z + 20, PROM_Z + 72):
            holes.append(ball_pocket(sx * WALL_SEAM_X, -WALL_T / 2, z))
    return union(holes)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

UP_Z, UP_FACE = (0, 0, 1), (0, -1, 0)   # wall: face (toward the stage, -y) up


def build() -> tuple[Manifold, dict[str, tuple[Manifold, tuple[int, int, int]]]]:
    floor = build_floor()
    floor -= extrude_xy(tenon_plan_world().offset(SLOT_CLEAR), PROM_Z - TENON - SLOT_CLEAR,
                        PROM_Z + 1)
    floor -= floor_pockets()
    for (x, y) in column_xy():
        floor -= ball_pocket(x, y, BAL_UNDER)
    wall = to_world(back_wall_local() - wall_pockets_local())

    big = 2000.0
    inner = base_plan() - beyond(SEAM_R)
    outer = beyond(SEAM_R)
    parts: dict[str, tuple[Manifold, tuple[int, int, int]]] = {}
    for fb, plan in (("front", inner), ("back", outer)):
        for lr, (x0, x1) in (("left", (0, big)), ("right", (-big, 0))):
            region = extrude_xy(plan ^ section([(x0, -big), (x1, -big), (x1, big), (x0, big)]),
                                -1, 500)
            parts[f"seating_floor_{fb}_{lr}"] = (floor ^ region, UP_Z)
    for lr, (x0, x1) in (("left", (WALL_SEAM_X, big)), ("centre", (-WALL_SEAM_X, WALL_SEAM_X)),
                         ("right", (-big, -WALL_SEAM_X))):
        parts[f"seating_wall_{lr}"] = (wall ^ box(x0, x1, -big, big, -1, 500), UP_FACE)
    bal = balcony()
    parts["seating_balcony"] = (bal, UP_Z)
    return floor + wall + bal, parts


def main(out_dir: str = str(OUT_DIR)) -> None:
    export_parts(*build(), out_dir, "seating")


if __name__ == "__main__":
    main(*sys.argv[1:])
