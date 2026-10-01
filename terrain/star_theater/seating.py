"""The Star Theater -- seating piece (part two).

The house side of Colette Du Bois' theater, built to face the stage piece
across the table: an orchestra pit along the front edge, four curved, raked
rows of velvet chairs with a centre aisle and side aisles, a tiled promenade at
the back and the auditorium's back wall with doors out to the lobby.

Run from the repo root:
    python -m terrain.star_theater.seating

Outputs (in output/star_theater/):
    seating_assembled.stl   the whole piece as it stands on the table (preview)
    print/seating_*.stl     printable parts, already rotated into print orientation

Coordinates follow the stage piece: +Y points away from the stage, so this
piece's front edge (the pit) is at y = 0 and its back wall at the far end.
Left/right are as seen from the audience (+x is the audience's left).

Rows give ~33 mm of standing room in front of each line of chairs, so 30 mm
bases fit between rows; aisles are 44 mm (centre) and 32 mm (sides).
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

from manifold3d import CrossSection, Manifold

from terrain.common.csg import (
    ball_pocket, box, circle_pts, cyl, extrude_xy, extrude_xz, extrude_yz, ring,
    section, sphere, star_pts, text_section, union, write_stl,
)
from terrain.star_theater.ornament import pilaster

# ---------------------------------------------------------------------------
# Key dimensions (mm)
# ---------------------------------------------------------------------------

HALF_W = 200.0
FLOOR = 8.0             # pit / front-row floor (the base plate thickness)
RISE = 6.0              # each row steps up this much
N_ROWS = 4
ROW_D = 46.0            # row depth: ~13 mm of chair + ~33 mm standing room
CENTER_Y = -900.0       # rows are arcs centred here, i.e. behind the stage
PIT_RAIL_R = (955.0, 958.0)
ROW1_R = 960.0          # front edge of row 1 (y = 60 on the centre line)
PROM_R = ROW1_R + N_ROWS * ROW_D
PROM_Z = FLOOR + N_ROWS * RISE
WALL_T = 12.0
WALL_Y = 292.0          # front face of the back wall
BACK_Y = WALL_Y + WALL_T
WALL_H = 96.0           # wall body height above the promenade
AISLE_HW = 22.0         # centre aisle half-width
SIDE_AISLE_X = 168.0    # side aisles run from here to the edge
SEAT_PITCH = 11.0

# Print layout: base split down the centre aisle and along the front edge of
# row 3 (the seam hides at the foot of a riser); wall split beside the centre
# pilasters. Joinery as on the stage: steel BB pockets + wall tenon in a slot.
SEAM_R = ROW1_R + 2 * ROW_D
WALL_SEAM_X = 42.0
TENON = 2.0
SLOT_CLEAR = 0.2

DOOR_C_HW, DOOR_C_SPRING = 20.0, 38.0     # centre double door: 40 x 58
DOOR_S_X, DOOR_S_HW, DOOR_S_SPRING = 182.0, 15.0, 35.0   # side doors: 30 x 50


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
        m += extrude_xy(band(row_r(k) - 0.8, row_r(k) + 1.5), row_z(k) - 1.0, row_z(k))
    # Plinth along the outside edges.
    m -= floor_grooves()
    m += carpet_runner()
    m += pit_rail()
    m += pit_props()
    for k in range(1, N_ROWS + 1):
        m += chair_row(k)
    return m


def floor_grooves() -> Manifold:
    """Pit planks, and a diamond-tiled promenade."""
    rng = random.Random(1858)
    cuts = []
    pit = section(arc_pts(PIT_RAIL_R[0]) + [(HALF_W, -1), (-HALF_W, -1)])
    lines = []
    for k in range(-16, 17):
        x = k * 12.0
        lines.append(box(x - 0.4, x + 0.4, -5, 80, FLOOR - 0.6, FLOOR + 1))
        y = rng.uniform(5, 40)
        while y < 70:
            lines.append(box(x, x + 12, y - 0.4, y + 0.4, FLOOR - 0.6, FLOOR + 1))
            y += rng.uniform(40, 70)
    cuts.append(union(lines) ^ extrude_xy(pit, 0, 50))
    # Promenade tiles: two families of 45-degree grooves.
    tiles = []
    step = 14.0
    for k in range(-40, 40):
        for sgn in (1, -1):
            g = box(-300, 300, -0.4, 0.4, PROM_Z - 0.6, PROM_Z + 1).rotate((0, 0, 45 * sgn))
            tiles.append(g.translate((0, 260 + k * step, 0)))
    prom = beyond(row_r(N_ROWS + 1) + 3) ^ section([(-500, 0), (500, 0), (500, WALL_Y),
                                                     (-500, WALL_Y)])
    prom = prom.offset(-1.5) - section([(-17, 0), (17, 0), (17, 400), (-17, 400)])  # not under the runner
    cuts.append(union(tiles) ^ extrude_xy(prom, 0, 100))
    return union(cuts)


def carpet_runner() -> Manifold:
    """A raised runner down the centre aisle, stepping with the rows."""
    parts = []
    strip = section([(-16, 0), (16, 0), (16, WALL_Y), (-16, WALL_Y)])
    for k in range(1, N_ROWS + 2):
        r0 = PIT_RAIL_R[1] if k == 1 else row_r(k) + 1.5
        r1 = row_r(k + 1) - 0.8 if k <= N_ROWS else 5000
        region = (beyond(r0) - beyond(r1)) ^ strip if k <= N_ROWS else beyond(r0) ^ strip
        parts.append(extrude_xy(region, row_z(k) - 0.1, row_z(k) + 0.5))
        parts.append(extrude_xy(ring(region, 0, -1.4), row_z(k) + 0.4, row_z(k) + 0.8))
    return union(parts)


def pit_rail() -> Manifold:
    """Curved rail between the pit and row 1, gaps at the aisles."""
    r0, r1 = PIT_RAIL_R
    parts = []
    for (xa, xb) in ((AISLE_HW + 1, SIDE_AISLE_X), (-SIDE_AISLE_X, -AISLE_HW - 1)):
        parts.append(extrude_xy(band(r0, r1, xa, xb), FLOOR - 0.1, FLOOR + 13))
        parts.append(extrude_xy(band(r0 - 0.8, r1 + 0.8, xa, xb), FLOOR + 13, FLOOR + 14.5))
        n = 5
        for i in range(n + 1):
            x = xa + (xb - xa) * i / n
            x = min(max(x, xa + 2), xb - 2)
            y = arc_y((r0 + r1) / 2, x)
            parts.append(box(x - 2, x + 2, y - 2.3, y + 2.3, FLOOR - 0.1, FLOOR + 15.5))
            parts.append(sphere(1.9, x, y, FLOOR + 17.0, 14))
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
# Orchestra pit
# ---------------------------------------------------------------------------


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


def pit_props() -> Manifold:
    z = FLOOR
    parts = [
        piano().rotate((0, 0, 180)).translate((-118, 22, z)),
        stool().translate((-118, 8, z)),
        podium().translate((0, 26, z)),
        drum().translate((140, 20, z)),
    ]
    for (x, y, rot) in ((-62, 28, 10), (-28, 40, 0), (36, 40, 0), (70, 28, -10), (104, 36, -15)):
        parts.append(music_stand().rotate((0, 0, 180 + rot)).translate((x, y, z)))
        dx, dy = 9 * math.sin(math.radians(rot)), 9 * math.cos(math.radians(rot))
        parts.append(stool().translate((x - dx, y - dy, z)))
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


def poster(cx: float, lines: list[tuple[str, float]]) -> Manifold:
    """A framed playbill with lettering, in relief."""
    z0, z1, hw = PROM_Z + 30, PROM_Z + 88, 22.0
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
    # Pediment over the centre doors, with a star in the tympanum.
    pz = PROM_Z + DOOR_C_SPRING + DOOR_C_HW + 6
    ped = section([(-34, pz), (34, pz), (0, pz + 17)])
    w += extrude_xz(section([(-36, pz - 2.5), (36, pz - 2.5), (36, pz), (-36, pz)]), 0, 5.0)
    w += extrude_xz(ring(ped, 0, -2.4), 0, 5.0)
    w += extrude_xz(ped, 0, 2.5)
    w += extrude_xz(section(star_pts(0, pz + 6, 4.6)), 0, 4.2)
    # Pilasters.
    for sx in (-1, 1):
        w += pilaster(sx * 32.0, PROM_Z, top, hw=6.0)
        w += pilaster(sx * 156.0, PROM_Z, top, hw=6.0)
    # Playbills and gas sconces.
    w += poster(-93.0, [("COLETTE", 7.0), ("DU BOIS", 5.0), ("*", 0), ("STAR OF", 4.2),
                        ("THE SHOW", 4.2)])
    w += poster(93.0, [("THE", 4.2), ("MECHANICAL", 5.0), ("DOVES", 7.0), ("*", 0),
                       ("NIGHTLY", 4.2)])
    for cx in (-127, -59, 59, 127):
        w += sconce(cx, PROM_Z + 68)
    # Cut the doorways, and trim anything poking past the wall ends.
    for d in doors:
        w -= extrude_xz(d ^ clip, -40, 40)
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
# Joinery
# ---------------------------------------------------------------------------


def floor_pockets() -> Manifold:
    holes = [ball_pocket(0, y, 4.0) for y in (25, 95, 200, 265)]
    for x in (-150, -95, -45, 45, 95, 150):
        holes.append(ball_pocket(x, arc_y(SEAM_R, x), 4.0))
    return union(holes)


def wall_pockets_local() -> Manifold:
    holes = []
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
    return floor + wall, parts


def main(out_dir: str = "output/star_theater") -> None:
    from terrain.common.printcheck import check, orient

    assembled, parts = build()
    out = Path(out_dir)
    n = write_stl(assembled, out / "seating_assembled.stl", "seating_assembled")
    print(f"seating_assembled  {n:7d} tris")
    print(f"{'part':24s} {'tris':>7s}  {'footprint':>13s} {'height':>6s}  overhangs")
    for name, (m, up) in parts.items():
        ntri = write_stl(orient(m, up), out / "print" / f"{name}.stl", name)
        rep = check(m, up)
        ncomp = len(m.decompose())
        fp = "x".join(f"{v:.0f}" for v in rep.footprint)
        ov = ", ".join(f"{o.area:.0f}mm2 {o.size[0]:.0f}x{o.size[1]:.0f}"
                       f"@({o.center[0]:.0f},{o.center[1]:.0f},{o.center[2]:.0f})"
                       for o in rep.overhangs[:4]) or "none"
        warn = "" if ncomp == 1 else f"  !! {ncomp} pieces"
        warn += "" if rep.fits((220, 220)) else "  !! exceeds 220 bed"
        print(f"{name:24s} {ntri:7d}  {fp:>13s} {rep.height:6.0f}  {ov}"
              f"  (minor {rep.minor_area:.0f}mm2){warn}")


if __name__ == "__main__":
    main(*sys.argv[1:])
