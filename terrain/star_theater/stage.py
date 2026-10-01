"""The Star Theater -- stage piece.

Colette Du Bois' theater in Malifaux: a ritzy proscenium stage with a curved
apron and an orchestra pit out front, a proscenium wall standing across the
middle of the base, and a backstage area behind it. Two side doors and the main arch let models move
between front-of-house and backstage.

Run from the repo root:
    python -m terrain.star_theater.stage

Outputs (in output/star_theater/):
    stage_assembled.stl   the whole piece as it stands on the table (preview)
    print/*.stl           12 printable parts, already rotated into print orientation

Designed for printing from the start: see PRINT LAYOUT below and the README.

Scale: ~32 mm "heroic" (Malifaux / D&D). 1 m in the world ~= 18 mm.
"""

from __future__ import annotations

import math
import random
import sys
import time
from pathlib import Path

from manifold3d import CrossSection, Manifold

from terrain.common.csg import (
    ball_pocket, box, circle_pts, cyl, ellipse, extrude_xy, extrude_xz, extrude_yz,
    revolve_profile, ring, section, segmental_arch_pts, sphere, star_pts,
    text_section, union, write_stl,
)
from terrain.star_theater.ornament import dove, pilaster
from terrain.star_theater.props import drum, music_stand, piano, podium, stool

# ---------------------------------------------------------------------------
# Key dimensions (mm)
# ---------------------------------------------------------------------------

HALF_W = 200.0          # base is 400 mm wide (x = -200 .. 200)
STAGE_H = 20.0          # stage deck height above the table
WALL_T = 20.0           # proscenium wall thickness
WALL_FRONT = 0.0        # wall front face at y = 0; wall occupies y = -WALL_T .. 0
WALL_TOP = 190.0        # top of cornice
BACK_Y = -116.0         # back edge of the backstage area (100 mm of backstage)
APRON_SIDE_Y = 85.0     # apron front edge at the far left/right
APRON_MID_Y = 112.0     # apron front edge at centre (curved thrust)

OPEN_HW = 100.0         # proscenium opening half-width (200 mm wide)
OPEN_SPRING = 120.0     # z where the arch springs
OPEN_RISE = 30.0        # segmental arch rise -> crown at z = 150

DOOR_X = 163.0          # side door centre (mirrored)
DOOR_HW = 18.0          # 36 mm wide doors (fits a 30 mm base with room)
DOOR_SPRING = 52.0      # round-headed door -> top at 70

BOX_X0, BOX_X1 = 133.0, 190.0   # opera box extents (+x side; mirrored)
BOX_FLOOR = 128.0       # top of the box floor (where models stand)
BOX_SLAB = 4.5          # balcony floor thickness; the corbel top is at BOX_FLOOR - BOX_SLAB
BOX_DEPTH = 42.0        # projection of the box floor in front of the wall (at the corners)
BOX_BOW = 6.0           # extra bulge of the bowed front
BOX_RAIL_H = 13.0
NICHE_D = 4.0           # depth of the arched niche behind each box
NICHE_SPRING = 143.0

# --- PRINT LAYOUT -----------------------------------------------------------
# The wall is split lengthwise at SPLIT_Y; both halves print lying down with the
# split face on the bed, so every feature that overhangs empty space (curtains,
# valance, marquee, finial) reaches back to that plane. The wall is also cut
# into left/centre/right at x = +-WALL_SEAM_X. The deck is cut into quarters at
# x = 0 and y = SPLIT_Y (that seam hides under the wall). Parts align with
# 4.5 mm steel BBs in hemispherical pockets (see csg.BALL_D), and the wall's
# 2 mm tenon drops into a matching slot in the deck.
SPLIT_Y = -WALL_T / 2
WALL_SEAM_X = OPEN_HW + 9.0
TENON = 2.0
SLOT_CLEAR = 0.2

PIT_D = 55.0            # orchestra pit: depth in front of the apron
PIT_HW = 146.0          # half-width (stops just short of the corner stairs)
PIT_FLOOR = 6.0         # pit floor height (the pit's base plate)
PIT_GATE = (118.0, 140.0)   # gaps in the pit rail, both sides

PLANK_W = 12.0
GROOVE_W, GROOVE_D = 0.8, 0.6

SEG = 48                # default circular segments for bigger curves


def mirror_x(m: Manifold) -> Manifold:
    return m.mirror((1, 0, 0))


def both_sides(m: Manifold) -> Manifold:
    return m + mirror_x(m)


# ---------------------------------------------------------------------------
# 2D outlines
# ---------------------------------------------------------------------------


def apron_curve(n: int = 80) -> list[tuple[float, float]]:
    """Front edge of the stage, left to right."""
    rise = APRON_MID_Y - APRON_SIDE_Y
    r = (HALF_W ** 2 + rise ** 2) / (2 * rise)
    cy = APRON_MID_Y - r
    a = math.degrees(math.asin(HALF_W / r))
    pts = circle_pts(0.0, cy, r, n, 90 + a, 90 - a)
    return pts


def apron_y_at(x: float) -> float:
    rise = APRON_MID_Y - APRON_SIDE_Y
    r = (HALF_W ** 2 + rise ** 2) / (2 * rise)
    return APRON_MID_Y - r + math.sqrt(r * r - x * x)


def deck_outline() -> CrossSection:
    pts = [(-HALF_W, BACK_Y), (HALF_W, BACK_Y)] + list(reversed(apron_curve()))
    return section(pts)


def opening_outline() -> CrossSection:
    """Proscenium opening in elevation (x, z), floor at STAGE_H."""
    pts = [(-OPEN_HW, STAGE_H - 30), (OPEN_HW, STAGE_H - 30)]
    pts += segmental_arch_pts(OPEN_HW, OPEN_SPRING, OPEN_RISE, 60)
    return section(pts)


def door_outline(cx: float) -> CrossSection:
    pts = [(cx - DOOR_HW, STAGE_H - 30), (cx + DOOR_HW, STAGE_H - 30)]
    pts += circle_pts(cx, DOOR_SPRING, DOOR_HW, 32, 0, 180)
    return section(pts)


def above_deck_xz() -> CrossSection:
    """Clip region for elevation work: everything above the deck."""
    return section([(-500, STAGE_H), (500, STAGE_H), (500, 1000), (-500, 1000)])


# ---------------------------------------------------------------------------
# Stage platform
# ---------------------------------------------------------------------------


def build_platform() -> Manifold:
    deck = deck_outline()
    body = extrude_xy(deck, 0.0, STAGE_H)

    # Nosing lip around the top edge (stepped underneath so it prints cleanly)
    # and a plinth at the bottom.
    body += extrude_xy(ring(deck, 0.8, -1.0), STAGE_H - 3.3, STAGE_H)
    body += extrude_xy(ring(deck, 1.6, -1.0), STAGE_H - 2.5, STAGE_H)
    body += extrude_xy(ring(deck, 1.2, -1.0), 0.0, 3.5)
    body += extrude_xy(ring(deck, 0.6, -1.0), 3.5, 4.5)

    body -= apron_panels(deck)
    body += apron_medallion()
    body += stairs()
    body -= floor_grooves()
    body -= trapdoor_cut()
    body += trapdoor_details()
    body += footlights()
    return body


def apron_panels(deck: CrossSection) -> Manifold:
    """Recessed panels around the platform's skirt."""
    skin = extrude_xy(ring(deck, 0.1, -1.0), 7.0, STAGE_H - 5.0)
    zones = []
    # Front curve: panels between stiles, skipping the stair zones and centre medallion.
    xs = [-145, -105, -65, -22, 22, 65, 105, 145]
    for a, b in zip(xs[:-1], xs[1:]):
        if a == -22:   # medallion bay
            continue
        zones.append(box(a + 3, b - 3, 0, 200, 0, 50))
    # Sides: panels along y.
    ys = [BACK_Y + 6, -70, -24, 22, 70]
    for a, b in zip(ys[:-1], ys[1:]):
        zones.append(box(-300, -190, a + 3, b - 3, 0, 50))
        zones.append(box(190, 300, a + 3, b - 3, 0, 50))
    # Back edge.
    for a in range(-190, 190, 48):
        zones.append(box(a + 3, a + 45, BACK_Y - 5, BACK_Y + 5, 0, 50))
    return skin ^ union(zones)


def apron_medallion() -> Manifold:
    """Star medallion on the centre of the apron front."""
    yc = APRON_MID_Y
    zc = STAGE_H / 2 + 0.5
    disc = ellipse(0, zc, 11, 6.5, 48)
    plate = extrude_xz(disc, yc - 3, yc + 1.2)
    plate += extrude_xz(ring(disc, 0, -1.2), yc - 3, yc + 2.0)
    plate += extrude_xz(section(star_pts(0, zc, 5.2, 2.4)), yc - 3, yc + 2.4)
    return plate


def stairs() -> Manifold:
    """Three steps down from each front corner of the apron."""
    parts = []
    x0, x1 = 152.0, 194.0
    back = apron_y_at(x0) - 12
    front0 = apron_y_at(x0)
    rise, tread = 5.0, 10.0
    for k in range(1, 4):
        top = STAGE_H - rise * k
        parts.append(box(x0, x1, back, front0 + tread * k, 0, top))
        # Little nosing on each step.
        parts.append(box(x0, x1, front0 + tread * k - 1.0, front0 + tread * k + 0.8,
                         top - 1.2, top))
    # Newel posts & balustrade-cheeks on the inner side of each stair.
    post_x = x0 - 2.5
    cheek = section([(back + 2, 0), (front0 + 31, 0), (front0 + 31, 8),
                     (front0 + 1, STAGE_H + 8), (back + 2, STAGE_H + 8)])
    parts.append(extrude_yz(cheek, post_x - 2.5, post_x + 2.5))
    parts.append(cyl(3.2, STAGE_H + 6, STAGE_H + 9, post_x, front0 + 2, segments=20))
    parts.append(sphere(2.6, post_x, front0 + 2, STAGE_H + 11, segments=16))
    parts.append(cyl(3.2, 6, 10, post_x, front0 + 29, segments=20))
    parts.append(sphere(2.6, post_x, front0 + 29, 12, segments=16))
    s = union(parts)
    return both_sides(s)


def floor_grooves() -> Manifold:
    """Plank lines running up/down stage with staggered butt joints."""
    rng = random.Random(1857)  # deterministic
    cuts = []
    z0, z1 = STAGE_H - GROOVE_D, STAGE_H + 1
    y_front = APRON_MID_Y + 5
    # Plank lines on multiples of PLANK_W, so the deck seam at x = 0 lands on one.
    n = int(HALF_W // PLANK_W)
    for k in range(-n, n + 1):
        x = k * PLANK_W
        cuts.append(box(x - GROOVE_W / 2, x + GROOVE_W / 2, BACK_Y - 2, y_front, z0, z1))
    # butt joints
    for i in range(-n - 1, n + 1):
        xa = i * PLANK_W
        y = BACK_Y + rng.uniform(10, 70)
        while y < APRON_MID_Y:
            cuts.append(box(xa, xa + PLANK_W, y - GROOVE_W / 2, y + GROOVE_W / 2, z0, z1))
            y += rng.uniform(60, 110)
    return union(cuts)


TRAP_C = (-60.0, 50.0)   # off-centre so the x = 0 deck seam misses it
TRAP_HW = 21.0


def trapdoor_cut() -> Manifold:
    cx, cy = TRAP_C
    outer = box(cx - TRAP_HW - 0.6, cx + TRAP_HW + 0.6, cy - TRAP_HW - 0.6, cy + TRAP_HW + 0.6,
                STAGE_H - 1.0, STAGE_H + 1)
    inner = box(cx - TRAP_HW + 0.6, cx + TRAP_HW - 0.6, cy - TRAP_HW + 0.6, cy + TRAP_HW - 0.6,
                STAGE_H - 2, STAGE_H + 2)
    return outer - inner


def trapdoor_details() -> Manifold:
    cx, cy = TRAP_C
    z = STAGE_H
    parts = []
    # Hinge straps on the upstage edge.
    for dx in (-12, 12):
        parts.append(box(cx + dx - 2.5, cx + dx + 2.5, cy - TRAP_HW + 1.5, cy - TRAP_HW + 9,
                         z - 0.2, z + 0.5))
        parts.append(box(cx + dx - 3, cx + dx + 3, cy - TRAP_HW - 0.2, cy - TRAP_HW + 1.8,
                         z - 0.2, z + 0.9))
    # Ring pull, lying flat, half sunk.
    torus = Manifold.revolve(section(circle_pts(2.4, 0, 0.55, 12)), 24)
    parts.append(torus.translate((cx, cy + TRAP_HW - 6, z)))
    parts.append(cyl(1.0, z - 0.2, z + 0.5, cx, cy + TRAP_HW - 8.2, segments=12))
    # Painted star marking (shallow raised) in the middle -- the magician's mark.
    parts.append(extrude_xy(ring(section(star_pts(cx, cy, 9.0)), 0, -0.9), z - 0.2, z + 0.4))
    return union(parts)


def footlights() -> Manifold:
    """Shell-hooded footlights following the curved apron edge."""
    # Solid quarter-dome hood (audience side) with the lamp resting on the base
    # plate in front of it: no hollow undersides to print.
    hood = Manifold.sphere(4.2, 28) ^ box(-5, 5, 0, 5, 0, 5)
    hood += box(-4.2, 4.2, -2.4, 4.2, -0.6, 0.6)     # base plate
    lamp = sphere(1.5, 0, -0.6, 2.1, 16)
    unit = hood + lamp
    parts = []
    xs = [x for x in range(-136, 137, 17) if abs(x) > 26]
    for x in xs:
        y = apron_y_at(x) - 5.5
        # Outward normal of the arc at x.
        rise = APRON_MID_Y - APRON_SIDE_Y
        r = (HALF_W ** 2 + rise ** 2) / (2 * rise)
        ang = math.degrees(math.atan2(x, y - (APRON_MID_Y - r) + 5.5))
        parts.append(unit.rotate((0, 0, -ang)).translate((x, y, STAGE_H + 0.6)))
    return union(parts)


# ---------------------------------------------------------------------------
# Orchestra pit (in front of the apron, part of the front deck pieces)
# ---------------------------------------------------------------------------


def _pit_front(x: float) -> float:
    return apron_y_at(x) + PIT_D


def pit_plan() -> CrossSection:
    n = 80
    xs = [-PIT_HW + 2 * PIT_HW * i / n for i in range(n + 1)]
    front = [(x, _pit_front(x)) for x in xs]
    back = [(x, apron_y_at(x) - 1.0) for x in reversed(xs)]
    return section(front + back)


def _rail_band(x0: float, x1: float, inner: float, outer: float) -> CrossSection:
    n = 30
    xs = [x0 + (x1 - x0) * i / n for i in range(n + 1)]
    return section([(x, _pit_front(x) + outer) for x in xs]
                   + [(x, _pit_front(x) - inner) for x in reversed(xs)])


def build_pit() -> Manifold:
    """Sunken pit: plank floor, rail with gates near each end, the band's kit."""
    z = PIT_FLOOR
    m = extrude_xy(pit_plan(), 0, z)
    # Planks running toward the audience, with staggered butt joints.
    rng = random.Random(1859)
    cuts = []
    n = int(PIT_HW // PLANK_W)
    for k in range(-n, n + 1):
        x = k * PLANK_W
        cuts.append(box(x - GROOVE_W / 2, x + GROOVE_W / 2, 60, 200, z - GROOVE_D, z + 1))
        y = 80 + rng.uniform(5, 40)
        while y < 170:
            cuts.append(box(x, x + PLANK_W, y - GROOVE_W / 2, y + GROOVE_W / 2, z - GROOVE_D, z + 1))
            y += rng.uniform(35, 60)
    m -= union(cuts) ^ extrude_xy(pit_plan().offset(-1.0), 0, 50)
    # Front rail (gaps for the gates) and the two end rails.
    parts = []
    runs = [(-PIT_HW, -PIT_GATE[1]), (-PIT_GATE[0], PIT_GATE[0]), (PIT_GATE[1], PIT_HW)]
    for x0, x1 in runs:
        parts.append(extrude_xy(_rail_band(x0, x1, 3.0, 0.0), z - 0.1, z + 13))
        parts.append(extrude_xy(_rail_band(x0, x1, 3.8, 0.8), z + 13, z + 14.5))
        for i in range(max(2, int((x1 - x0) // 40) + 1)):
            k = max(2, int((x1 - x0) // 40) + 1)
            x = x0 + 2 + (x1 - x0 - 4) * i / (k - 1)
            y = _pit_front(x) - 1.5
            parts.append(box(x - 2, x + 2, y - 2.3, y + 2.3, z - 0.1, z + 15.5))
            parts.append(sphere(1.9, x, y, z + 17.0, 14))
    for sx in (-1, 1):
        x_out = sx * PIT_HW
        x_in = sx * (PIT_HW - 3)
        y0, y1 = apron_y_at(PIT_HW) - 1, _pit_front(PIT_HW)
        parts.append(box(x_in, x_out, y0, y1, z - 0.1, z + 13))
        parts.append(box(x_in - sx * 0.8, x_out + sx * 0.8, y0, y1 + 0.8, z + 13, z + 14.5))
    m += union(parts)
    # The band.
    def at(x, off):
        return (x, apron_y_at(x) + off)
    kit = [
        piano().rotate((0, 0, 180)).translate((*at(-88, 22), z)),
        stool().translate((*at(-88, 8), z)),
        podium().rotate((0, 0, 180)).translate((*at(0, 38), z)),
        drum().translate((*at(104, 16), z)),
    ]
    for (x, off, rot) in ((-46, 30, 4), (32, 33, 0), (62, 27, -6), (-110, 22, 10)):
        kit.append(music_stand().rotate((0, 0, 180 + rot)).translate((*at(x, off), z)))
        dx, dy = 9 * math.sin(math.radians(rot)), 9 * math.cos(math.radians(rot))
        px, py = at(x, off)
        kit.append(stool().translate((px - dx, py - dy, z)))
    m += union(kit)
    return m


# ---------------------------------------------------------------------------
# Backstage props (part of the platform piece)
# ---------------------------------------------------------------------------


def crate(s: float) -> Manifold:
    """Planked crate with recessed faces and a diagonal brace, sitting at origin."""
    c = box(-s / 2, s / 2, -s / 2, s / 2, 0, s)
    f = 2.2
    d = 0.9
    cuts = [
        box(-s / 2 + f, s / 2 - f, s / 2 - d, s / 2 + 1, f, s - f),
        box(-s / 2 + f, s / 2 - f, -s / 2 - 1, -s / 2 + d, f, s - f),
        box(s / 2 - d, s / 2 + 1, -s / 2 + f, s / 2 - f, f, s - f),
        box(-s / 2 - 1, -s / 2 + d, -s / 2 + f, s / 2 - f, f, s - f),
        box(-s / 2 + f, s / 2 - f, -s / 2 + f, s / 2 - f, s - d, s + 1),
    ]
    c -= union(cuts)
    diag_len = math.hypot(s - 2 * f, s - 2 * f)
    brace = box(-diag_len / 2, diag_len / 2, -1, 1, -1.1, 1.1)
    for rot, trans in [
        ((90, 45, 0), (0, s / 2 - d / 2, s / 2)),
        ((90, -45, 0), (0, -s / 2 + d / 2, s / 2)),
        ((90, 45, 90), (s / 2 - d / 2, 0, s / 2)),
        ((90, -45, 90), (-s / 2 + d / 2, 0, s / 2)),
    ]:
        b = brace.rotate(rot).translate(trans)
        c += b ^ box(-s / 2, s / 2, -s / 2, s / 2, 0, s)
    return c


def magic_cabinet() -> Manifold:
    """An upright illusionist's cabinet -- Colette's disappearing act."""
    w, d, h = 30.0, 26.0, 62.0
    cab = box(-w / 2, w / 2, -d / 2, d / 2, 0, h)
    # Plinth (solid to the floor, so nothing overhangs).
    cab += box(-w / 2 - 1.2, w / 2 + 1.2, -d / 2 - 1.2, d / 2 + 1.2, 0, 4)
    cab += box(-w / 2 - 0.6, w / 2 + 0.6, -d / 2 - 0.6, d / 2 + 0.6, 4, 4.6)
    # Crown moulding and dome.
    cab += box(-w / 2 - 0.7, w / 2 + 0.7, -d / 2 - 0.7, d / 2 + 0.7, h - 3.7, h - 3)
    cab += box(-w / 2 - 1.4, w / 2 + 1.4, -d / 2 - 1.4, d / 2 + 1.4, h - 3, h)
    cab += box(-w / 2 - 0.8, w / 2 + 0.8, -d / 2 - 0.8, d / 2 + 0.8, h, h + 1.5)
    dome = Manifold.sphere(1, 32).scale((w / 2 - 2, d / 2 - 2, 7)) ^ box(-50, 50, -50, 50, 0, 50)
    cab += dome.translate((0, 0, h + 1.5))
    cab += sphere(2, 0, 0, h + 9.5, 16)
    # Front doors (facing +y): two panels with stars, and a split line.
    yf = d / 2
    cab -= box(-0.4, 0.4, yf - 0.6, yf + 1, 8, h - 5)
    for sx in (-1, 1):
        cx = sx * w / 4
        panel = section([(cx - 5.5, 9), (cx + 5.5, 9), (cx + 5.5, h - 6), (cx - 5.5, h - 6)])
        cab -= extrude_xz(panel, yf - 0.8, yf + 1)
        cab += extrude_xz(section(star_pts(cx, (h + 3) / 2 + 6, 4.2)), yf - 1, yf + 0.2)
        cab += extrude_xz(section(star_pts(cx, (h + 3) / 2 - 12, 2.6)), yf - 1, yf + 0.2)
        cab += cyl(0.8, 0, 2, 0, 0, segments=10).rotate((-90, 0, 0)).translate(
            (sx * 2.2, yf - 0.5, h / 2))
    return cab


def trunk() -> Manifold:
    """Costume trunk with a barrel lid."""
    w, d, h = 34.0, 18.0, 13.0
    t = box(-w / 2, w / 2, -d / 2, d / 2, 0, h)
    lid = Manifold.cylinder(w, d / 2, d / 2, 32).rotate((0, 90, 0)).translate((-w / 2, 0, h))
    lid = lid ^ box(-w, w, -d, d, h, h + d)
    t += lid
    # Lid seam.
    t -= box(-w, w, -d, d, h - 0.4, h + 0.4) - box(-w / 2 + 0.6, w / 2 - 0.6, -d / 2 + 0.6,
                                                   d / 2 - 0.6, 0, 100)
    # Straps.
    for x in (-w / 2 + 6, w / 2 - 6):
        strap = box(x - 1.5, x + 1.5, -d / 2 - 0.6, d / 2 + 0.6, 0, h)
        strap += (Manifold.cylinder(3, d / 2 + 0.6, d / 2 + 0.6, 32).rotate((0, 90, 0))
                  .translate((x - 1.5, 0, h)) ^ box(-w, w, -d, d, h, h + d))
        t += strap
    # Corner caps.
    for sx in (-1, 1):
        t += box(sx * w / 2 - 2.5, sx * w / 2 + 2.5, -d / 2 - 0.5, d / 2 + 0.5, 0, 3)\
            ^ box(-w / 2 - 0.5, w / 2 + 0.5, -d, d, 0, 3)
    return t


def backstage_props() -> Manifold:
    z = STAGE_H
    parts = [
        crate(26).translate((-178, BACK_Y + 18, z)),
        crate(22).rotate((0, 0, 8)).translate((-178, BACK_Y + 18, z + 26 - 0.9)),
        crate(20).rotate((0, 0, -8)).translate((-150, BACK_Y + 16, z)),
        magic_cabinet().rotate((0, 0, 200)).translate((172, BACK_Y + 22, z)),
        trunk().rotate((0, 0, 6)).translate((128, BACK_Y + 13, z)),
    ]
    return union(parts)


# ---------------------------------------------------------------------------
# Proscenium wall
# ---------------------------------------------------------------------------


def wall_body() -> Manifold:
    w = box(-HALF_W, HALF_W, -WALL_T, WALL_FRONT, STAGE_H, WALL_TOP - 12)
    # Baseboard & dado rail along the front (cut away at openings later).
    w += box(-HALF_W, HALF_W, 0, 1.5, STAGE_H, STAGE_H + 6)
    w += extrude_yz(section([(0, 44), (2.2, 45), (2.2, 47), (0, 48.5)]), -HALF_W, HALF_W)
    # Back face: base + timber framing (studs + a rail) for a rougher backstage look.
    w += box(-HALF_W, HALF_W, -WALL_T - 1.2, -WALL_T, STAGE_H, STAGE_H + 5)
    for x in range(-195, 200, 30):
        w += box(x - 2.5, x + 2.5, -WALL_T - 2.2, -WALL_T, STAGE_H, WALL_TOP - 12)
    w += box(-HALF_W, HALF_W, -WALL_T - 2.2, -WALL_T, 104, 109)
    return w


def cornice() -> Manifold:
    """Stepped crown cornice + dentils running along the top front of the wall."""
    z0 = WALL_TOP - 14
    prof = section([
        (-WALL_T - 1.5, z0), (0, z0), (1.5, z0), (1.5, z0 + 2.5), (3.0, z0 + 4.0),
        (5.5, z0 + 6.5), (5.5, z0 + 8.0), (7.5, z0 + 10.0), (8.5, z0 + 10.0),
        (8.5, WALL_TOP), (-WALL_T - 2.5, WALL_TOP), (-WALL_T - 2.5, WALL_TOP - 3),
        (-WALL_T - 1.5, WALL_TOP - 4),
    ])
    c = extrude_yz(prof, -HALF_W, HALF_W)
    dent = []
    x = -HALF_W + 2
    while x < HALF_W - 4:
        dent.append(box(x, x + 3, 0, 3.2, z0 - 3.5, z0 + 0.5))
        x += 6
    c += union(dent)
    return c


def proscenium_frame() -> Manifold:
    """Stepped moulding around the main arch, keystone, pilasters."""
    op = opening_outline()
    clip = above_deck_xz()
    layers = [
        (0, 13, 1.8),
        (1.5, 11, 3.6),
        (4.5, 8.0, 5.4),     # raised bead
        (11, 13, 2.6),
    ]
    parts = []
    for inner, outer, proud in layers:
        parts.append(extrude_xz(ring(op, outer, inner) ^ clip, 0, proud))
    # Plinth blocks at the foot of the frame.
    for sx in (-1, 1):
        parts.append(box(sx * OPEN_HW, sx * (OPEN_HW + 14.5), -0.1, 6.5, STAGE_H, STAGE_H + 14))
    # Keystone.
    crown = OPEN_SPRING + OPEN_RISE
    ks = section([(-7, crown - 2), (7, crown - 2), (10, crown + 16), (-10, crown + 16)])
    parts.append(extrude_xz(ks, 0, 7.0))
    parts.append(extrude_xz(section(star_pts(0, crown + 7, 5.2)), 0, 8.4))
    # Pilasters either side.
    for sx in (-1, 1):
        parts.append(pilaster(sx * 121.0, STAGE_H, WALL_TOP - 14))
    # Corner pilasters at the wall ends.
    for sx in (-1, 1):
        parts.append(box(sx * 191, sx * HALF_W, -0.1, 3.0, STAGE_H, WALL_TOP - 14))
        parts.append(box(sx * 190, sx * HALF_W, -0.1, 4.0, STAGE_H, STAGE_H + 9))
        parts.append(box(sx * 190, sx * HALF_W, -0.1, 4.5, WALL_TOP - 21, WALL_TOP - 14))
    return union(parts)


def curtains() -> Manifold:
    """Tied-back main drapes inside the arch, with a swagged valance.

    Everything here fills solidly through the split plane (SPLIT_Y), so both the
    front and back wall halves print without supports: the front half shows
    folds on the audience side, the back half shows them backstage.
    """
    parts = []
    # --- side drapes (build the +x one, mirror) ---
    jamb = OPEN_HW + 6.0          # buried into the jamb
    xs = []
    x = jamb
    while x > OPEN_HW - 40:
        xs.append(x)
        x -= 0.7
    amp, lam = 2.0, 7.0
    front = [(x, -4.5 + amp * math.sin(2 * math.pi * x / lam)) for x in xs]
    back = [(x, -15.5 - amp * math.sin(2 * math.pi * x / lam + 1.3)) for x in reversed(xs)]
    folds = extrude_xy(section(front + back), STAGE_H, OPEN_SPRING + OPEN_RISE + 6)

    tie_z = 64.0

    def inner_edge(z: float) -> float:
        """Distance the drape reaches into the opening, as a function of height."""
        if z <= tie_z:
            t = (z - STAGE_H) / (tie_z - STAGE_H)
            return 24 - 12 * t ** 0.8
        t = (z - tie_z) / (OPEN_SPRING + OPEN_RISE - tie_z)
        return 12 + 26 * t ** 1.6

    sil = []
    zs = [STAGE_H + i * (OPEN_SPRING + OPEN_RISE + 8 - STAGE_H) / 60 for i in range(61)]
    for z in zs:
        sil.append((OPEN_HW - inner_edge(min(z, OPEN_SPRING + OPEN_RISE)), z))
    sil += [(jamb + 2, zs[-1]), (jamb + 2, STAGE_H)]
    drape = folds ^ extrude_xz(section(sil), -WALL_T, 0)
    # Puddle at the floor.
    drape += extrude_xz(section([(OPEN_HW - 25, STAGE_H), (jamb, STAGE_H), (jamb, STAGE_H + 2.5),
                                 (OPEN_HW - 23.5, STAGE_H + 2.5)]), -17.5, -2.5)
    # Tie-back band right round the drape, and a tassel (relief, front side).
    band_x = OPEN_HW - 12.5
    drape += box(band_x - 1, jamb, -18.5, -1.5, tie_z - 1.6, tie_z + 1.6)
    tx = band_x + 1.5
    tassel = (section(circle_pts(tx, tie_z - 1.6, 1.6, 16))
              + section([(tx - 0.6, tie_z - 2), (tx + 0.6, tie_z - 2), (tx + 1.6, tie_z - 9),
                         (tx - 1.6, tie_z - 9)]))
    drape += extrude_xz(tassel, SPLIT_Y, -0.8)
    parts.append(both_sides(drape))

    # --- swagged valance: three tiers on the audience side, one behind ---
    crown = OPEN_SPRING + OPEN_RISE
    n_swags = 5
    sw = 2 * OPEN_HW / n_swags
    tiers = [(-14.5, -4.0, 128.0, 13.0), (-4.0, -2.0, 132.0, 8.5), (-2.0, -0.3, 136.0, 4.0)]
    for y0, y1, base_z, depth in tiers:
        pts = []
        for i in range(n_swags):
            x0 = -OPEN_HW + i * sw
            for k in range(13):
                t = k / 12
                pts.append((x0 + t * sw, base_z - depth * math.sin(math.pi * t)))
        pts += [(OPEN_HW + 6, base_z), (OPEN_HW + 6, crown + 10), (-OPEN_HW - 6, crown + 10),
                (-OPEN_HW - 6, base_z)]
        parts.append(extrude_xz(section(pts), y0, y1))
    # Tassels at the swag junctions, in relief down to the split plane.
    for i in range(1, n_swags):
        x = -OPEN_HW + i * sw
        t = (section(circle_pts(x, 134.0, 1.8, 16))
             + section([(x - 0.8, 133), (x + 0.8, 133), (x + 1.8, 124), (x - 1.8, 124)]))
        parts.append(extrude_xz(t, SPLIT_Y, -0.6))
    return union(parts)


def doors() -> Manifold:
    """Frames for the two side doors (the openings are cut later)."""
    parts = []
    clip = above_deck_xz()
    for sx in (-1, 1):
        do = door_outline(sx * DOOR_X)
        parts.append(extrude_xz(ring(do, 4.5, 0) ^ clip, 0, 2.2))
        parts.append(extrude_xz(ring(do, 3.0, 1.2) ^ clip, 0, 3.4))
        # Little keystone.
        top = DOOR_SPRING + DOOR_HW
        ks = section([(sx * DOOR_X - 3, top - 1), (sx * DOOR_X + 3, top - 1),
                      (sx * DOOR_X + 4.2, top + 6), (sx * DOOR_X - 4.2, top + 6)])
        parts.append(extrude_xz(ks, 0, 4.2))
        # Back-face frame (backstage side).
        parts.append(extrude_xz(ring(do, 3.5, 0) ^ clip, -WALL_T - 2.6, -WALL_T))
    return union(parts)


def _box_plan() -> tuple[CrossSection, list[tuple[float, float]]]:
    """Plan outline of an opera box (+x side): rectangle with a bowed front."""
    x0, x1 = BOX_X0, BOX_X1
    bow = []
    for i in range(25):
        t = i / 24
        bow.append((x0 + t * (x1 - x0), BOX_DEPTH + BOX_BOW * math.sin(math.pi * t)))
    return section([(x0, 0.0)] + bow + [(x1, 0.0)]), bow


def _box_pin_xy() -> list[tuple[float, float]]:
    xc = (BOX_X0 + BOX_X1) / 2
    return [(xc - 18, 20.0), (xc + 18, 20.0)]


def box_corbel(sx: int) -> Manifold:
    """The bracket under an opera box. It's part of the wall's front half and
    carries the separately printed balcony on its flat top."""
    x0, x1 = BOX_X0, BOX_X1
    xc, hw = (x0 + x1) / 2, (x1 - x0) / 2
    plan, _ = _box_plan()
    top = BOX_FLOOR - BOX_SLAB
    drop = BOX_DEPTH + BOX_BOW + 1.0          # 45 degrees (ish) to the wall
    strip = box(DOOR_X - DOOR_HW - 4, DOOR_X + DOOR_HW + 4, -1.0, 0.0, top - drop, top - drop + 1)
    m = (strip + extrude_xy(plan, top - 1.0, top)).hull()
    # Moulded lip just under the balcony.
    m += extrude_xy(plan.offset(0.8) ^ section([(0, -0.5), (500, -0.5), (500, 99), (0, 99)]),
                    top - 1.8, top - 0.8)
    # Decorative ribs on the underside.
    for dx in (-hw + 6, 0, hw - 6):
        x = xc + dx
        ymax = BOX_DEPTH + BOX_BOW * math.sin(math.pi * (x - x0) / (x1 - x0))
        rib = section([(0, top - drop), (0.8, top - drop - 1), (ymax + 1.0, top - 1.8),
                       (ymax + 1.0, top - 0.8), (0, top - 0.8)])
        m += extrude_yz(rib, x - 1.6, x + 1.6)
        m += sphere(1.6, x, 1.0, top - drop, 10)
    return m if sx > 0 else mirror_x(m)


def balcony(sx: int) -> Manifold:
    """The opera box floor + balustrade: printed upright, pinned onto its corbel.

    Floor is ~56 x 45 mm inside the rails: room for a 40 mm base.
    """
    x0, x1 = BOX_X0, BOX_X1
    plan, bow = _box_plan()
    fb = BOX_FLOOR - BOX_SLAB
    nx0, nx1 = x0 + 4 + 0.25, x1 - 4 - 0.25     # tongue that sits in the wall niche
    floor_cs = plan + section([(nx0, -NICHE_D + 0.25), (nx1, -NICHE_D + 0.25), (nx1, 0.5),
                               (nx0, 0.5)])
    m = extrude_xy(floor_cs, fb, BOX_FLOOR)
    open_back = section([(x0 - 5, 2.8), (x1 + 5, 2.8), (x1 + 5, 99), (x0 - 5, 99)])
    rails = ring(plan, 0.0, -2.6) ^ open_back
    m += extrude_xy(rails, BOX_FLOOR, BOX_FLOOR + 1.6)
    m += extrude_xy(rails, BOX_FLOOR + BOX_RAIL_H - 2.2, BOX_FLOOR + BOX_RAIL_H)
    baluster = revolve_profile([
        (0, 0), (1.4, 0), (1.4, 0.6), (0.85, 1.2), (0.9, 2.0), (1.55, 4.3), (1.3, 6.0),
        (0.8, 7.6), (0.8, 8.4), (1.15, 8.9), (1.15, 9.6), (0, 9.6),
    ], 16).scale((1, 1, (BOX_RAIL_H - 2.2 - 1.6) / 9.6))
    pts = []
    for i in range(1, 12):
        t = i / 12
        pts.append((x0 + t * (x1 - x0), BOX_DEPTH + BOX_BOW * math.sin(math.pi * t) - 1.3))
    for y in (9.0, 17.0, 25.0, 33.0):
        pts.append((x0 + 1.3, y))
        pts.append((x1 - 1.3, y))
    for (x, y) in pts:
        m += baluster.translate((x, y, BOX_FLOOR + 1.6))
    # Square newel posts at all four corners, with ball finials.
    for (x, y) in [(x0 + 1.9, BOX_DEPTH - 1.6), (x1 - 1.9, BOX_DEPTH - 1.6),
                   (x0 + 1.9, 3.7), (x1 - 1.9, 3.7)]:
        m += box(x - 1.9, x + 1.9, y - 1.9, y + 1.9, BOX_FLOOR, BOX_FLOOR + BOX_RAIL_H + 1)
        m += sphere(1.8, x, y, BOX_FLOOR + BOX_RAIL_H + 2.0, 14)
    # Ball pockets underneath.
    for (x, y) in _box_pin_xy():
        m -= ball_pocket(x, y, fb)
    return m if sx > 0 else mirror_x(m)


def _niche_outline(sx: int) -> CrossSection:
    xc = (BOX_X0 + BOX_X1) / 2
    r = (BOX_X1 - BOX_X0) / 2 - 4
    pts = [(xc - r, BOX_FLOOR - BOX_SLAB), (xc + r, BOX_FLOOR - BOX_SLAB)]
    pts += circle_pts(xc, NICHE_SPRING, r, 24, 0, 180)
    cs = section(pts)
    return cs if sx > 0 else cs.mirror((1, 0))


def box_niches() -> Manifold:
    """Recesses cut into the wall behind each opera box."""
    return union(extrude_xz(_niche_outline(sx), -NICHE_D, 1.0) for sx in (-1, 1))


def box_niche_trim() -> Manifold:
    """Arched moulding round each niche."""
    out = []
    for sx in (-1, 1):
        trim = ring(_niche_outline(sx), 2.2, 0) ^ section(
            [(-500, BOX_FLOOR + 1), (500, BOX_FLOOR + 1), (500, 300), (-500, 300)])
        out.append(extrude_xz(trim, 0, 1.6))
    return union(out)


def box_doors() -> Manifold:
    """Panelled door at the back of each niche (relief; added after the niche cut)."""
    out = []
    xc = (BOX_X0 + BOX_X1) / 2
    for sx in (-1, 1):
        # Door into the box from the corridor behind (relief only).
        dx = sx * xc
        door = section([(dx - 10, BOX_FLOOR), (dx + 10, BOX_FLOOR)]
                       + circle_pts(dx, BOX_FLOOR + 22, 10, 16, 0, 180))
        d = extrude_xz(door, -NICHE_D - 0.5, -NICHE_D + 1.0)
        for px in (dx - 4.8, dx + 4.8):
            panel = section([(px - 3, BOX_FLOOR + 3), (px + 3, BOX_FLOOR + 3),
                             (px + 3, BOX_FLOOR + 25), (px - 3, BOX_FLOOR + 25)])
            d -= extrude_xz(panel, -NICHE_D + 0.4, -NICHE_D + 2)
        d += sphere(1.0, dx - sx * 7.6, -NICHE_D + 1.0, BOX_FLOOR + 16, 10)
        out.append(d)
    return union(out)


def marquee() -> Manifold:
    """'THE STAR' marquee crest, standing proud of the cornice over the arch."""
    z0, z1 = 164.0, 199.0
    hw = 56.0
    yf = 10.5                                   # front face of the board
    top = segmental_arch_pts(hw, z1 - 5, 7.0, 40)
    board_cs = section([(-hw, z0), (hw, z0)] + top)
    m = extrude_xz(board_cs, SPLIT_Y, yf)
    # 45-degree chamfer under the board so it prints without supports.
    m += extrude_yz(section([(0, z0 - yf), (yf, z0), (yf, z0 + 1), (0, z0 + 1)]), -hw, hw)
    m += extrude_xz(ring(board_cs, 0.0, -2.4), yf - 0.2, yf + 1.6)
    m += extrude_xz(ring(board_cs, -3.6, -4.6), yf - 0.2, yf + 1.0)
    # Bulbs around the border, resampled at even spacing.
    pts = [tuple(p) for poly in board_cs.offset(-1.2).to_polygons() for p in poly]
    bulbs, acc, spacing = [], 0.0, 6.0
    for (a, b) in zip(pts, pts[1:] + pts[:1]):
        seg = math.dist(a, b)
        while acc <= seg:
            t = acc / seg if seg else 0
            bulbs.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
            acc += spacing
        acc -= seg
    for (x, z) in bulbs:
        m += sphere(1.3, x, yf + 1.4, z, 12)
    # Lettering.
    m += extrude_xz(text_section("THE STAR", 12.0, 0, (z0 + z1) / 2 - 1.0, spacing=0.08,
                                 mirror=True),
                    yf - 0.2, yf + 1.8)
    # Side scrolls bracing the board.
    for sx in (-1, 1):
        sc = section([(sx * hw, z0), (sx * (hw + 12), z0 + 12), (sx * (hw + 12), z0 + 15),
                      (sx * hw, z0 + 26)])
        m += extrude_xz(sc, SPLIT_Y, yf - 1.5)
        m += extrude_xz(section(circle_pts(sx * (hw + 9.5), z0 + 13.5, 3.4, 20)), yf - 2, yf + 0.4)
        m -= extrude_xz(section(circle_pts(sx * (hw + 9.5), z0 + 13.5, 1.4, 16)), yf - 0.6, yf + 1)
    # Star finial.
    crest_z = z1 + 2.0
    m += extrude_xz(section(star_pts(0, crest_z + 9, 9.0)), SPLIT_Y, -4.0)
    m += extrude_xz(section(star_pts(0, crest_z + 9, 5.5)), -4.5, -2.6)
    m += extrude_xz(section([(-5, z1 - 1), (5, z1 - 1), (2.5, crest_z + 6.0),
                             (-2.5, crest_z + 6.0)]), SPLIT_Y, -3.0)
    return m


def tenon_plan() -> CrossSection:
    """Footprint of the wall's solid runs at deck level (between the openings)."""
    runs = [(-HALF_W, -DOOR_X - DOOR_HW), (-DOOR_X + DOOR_HW, -OPEN_HW),
            (OPEN_HW, DOOR_X - DOOR_HW), (DOOR_X + DOOR_HW, HALF_W)]
    return union(extrude_xy(section([(a, -WALL_T), (b, -WALL_T), (b, 0), (a, 0)]), 0, 1)
                 for a, b in runs).project()


def build_wall() -> Manifold:
    w = wall_body()
    w += cornice()
    w += proscenium_frame()
    w += doors()
    w += box_niche_trim()
    w -= box_niches()
    # Cut the openings (main arch + doors) through everything on the wall.
    cuts = extrude_xz(opening_outline() ^ above_deck_xz(), -40, 40)
    for sx in (-1, 1):
        cuts += extrude_xz(door_outline(sx * DOOR_X) ^ above_deck_xz(), -40, 40)
    w -= cuts
    # Things that live inside / in front of the openings get added after the cut.
    w += curtains()
    w += box_corbel(1) + box_corbel(-1)
    w += box_doors()
    w += marquee()
    for sx in (-1, 1):
        w += dove(sx * 88.0, 151.0, 28.0, -sx, 0.0)
    # Back of the arch: simple frame on the backstage side.
    w += extrude_xz(ring(opening_outline(), 4.0, 0) ^ above_deck_xz(), -WALL_T - 2.6, -WALL_T)
    w += pin_rail()
    # Tenon that drops into the deck slot.
    w += extrude_xy(tenon_plan(), STAGE_H - TENON, STAGE_H + 0.01)
    return w


def pin_rail() -> Manifold:
    """Pin rail with belaying pins and rope coils on the back of the wall, all in
    relief so it prints face-up with the back half."""
    yb = -WALL_T
    parts = [box(-190, -120, yb - 7, yb, 84, 89)]
    for x in range(-186, -122, 7):
        pin = (section([(x - 1.0, 78), (x + 1.0, 78), (x + 1.0, 95), (x - 1.0, 95)])
               + section(circle_pts(x, 95, 1.4, 12)))
        parts.append(extrude_xz(pin, yb, yb - 5.0))
    for x in (-185, -125):
        br = section([(yb, 72), (yb, 84), (yb - 7, 84), (yb - 1, 72)])
        parts.append(extrude_yz(br, x - 1.5, x + 1.5))
    # Coiled ropes hanging off some of the pins.
    for x in (-179, -158, -137):
        coil = ellipse(x, 76, 3.6, 6.0, 24) - ellipse(x, 76, 2.0, 4.2, 20)
        parts.append(extrude_xz(coil, yb, yb - 6.2))
    return union(parts)


# ---------------------------------------------------------------------------
# Joinery: slots and ball pockets
# ---------------------------------------------------------------------------


def deck_slot() -> Manifold:
    return extrude_xy(tenon_plan().offset(SLOT_CLEAR), STAGE_H - TENON - SLOT_CLEAR,
                      STAGE_H + 1)


def deck_pin_holes() -> Manifold:
    z = 9.0
    holes = [ball_pocket(0, y, z) for y in (-95, -45, 25, 65, 100)]
    holes.append(ball_pocket(0, apron_y_at(0) + PIT_D / 2, PIT_FLOOR / 2))
    holes += [ball_pocket(x, SPLIT_Y, z) for x in (-175, -125, -75, -30, 30, 75, 125, 175)]
    return union(holes)


def wall_pin_holes() -> Manifold:
    holes = []
    # Front half <-> back half (perpendicular to the split plane).
    front_back = [(118, 40), (118, 150), (196, 40), (196, 150), (163, 100),
                  (104.5, 50), (104.5, 100), (0, 172), (50, 166), (85, 165)]
    for (x, z) in front_back:
        for sx in ((-1, 1) if x else (1,)):
            holes.append(ball_pocket(sx * x, SPLIT_Y, z))
    # Side sections <-> centre section.
    for sx in (-1, 1):
        for z in (50, 110, 168):
            for y in (SPLIT_Y / 2, SPLIT_Y * 1.5):
                holes.append(ball_pocket(sx * WALL_SEAM_X, y, z))
    # Corbel tops <-> balconies.
    for sx in (-1, 1):
        for (x, y) in _box_pin_xy():
            top = BOX_FLOOR - BOX_SLAB
            holes.append(ball_pocket(sx * x, y, top))
    return union(holes)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

UP_Z, UP_FRONT, UP_BACK = (0, 0, 1), (0, 1, 0), (0, -1, 0)


def build() -> tuple[Manifold, dict[str, tuple[Manifold, tuple[int, int, int]]]]:
    """Returns (assembled model, {part name: (part in assembled coords, print 'up')}).

    Left/right are as seen from the audience (+x is on the audience's left).
    """
    t0 = time.time()
    platform = build_platform() + backstage_props() + build_pit()
    platform = platform - deck_slot() - deck_pin_holes()
    print(f"  platform built in {time.time() - t0:.1f}s", file=sys.stderr)
    t0 = time.time()
    wall = build_wall() - wall_pin_holes()
    balconies = {"left": balcony(1), "right": balcony(-1)}
    print(f"  wall built in {time.time() - t0:.1f}s", file=sys.stderr)

    big = 1000.0
    parts: dict[str, tuple[Manifold, tuple[int, int, int]]] = {}
    for fb, (y0, y1) in {"front": (SPLIT_Y, big), "back": (-big, SPLIT_Y)}.items():
        for lr, (x0, x1) in {"left": (0, big), "right": (-big, 0)}.items():
            piece = platform ^ box(x0, x1, y0, y1, -1, big)
            parts[f"deck_{fb}_{lr}"] = (piece, UP_Z)
    for fb, (y0, y1), up in (("front", (SPLIT_Y, big), UP_FRONT),
                             ("back", (-big, SPLIT_Y), UP_BACK)):
        for lr, (x0, x1) in {"left": (WALL_SEAM_X, big),
                             "centre": (-WALL_SEAM_X, WALL_SEAM_X),
                             "right": (-big, -WALL_SEAM_X)}.items():
            parts[f"wall_{fb}_{lr}"] = (wall ^ box(x0, x1, y0, y1, -1, big), up)
    for lr, m in balconies.items():
        parts[f"balcony_{lr}"] = (m, UP_Z)
    assembled = platform + wall + union(balconies.values())
    return assembled, parts


def main(out_dir: str = "output/star_theater") -> None:
    from terrain.common.printcheck import check, orient

    assembled, parts = build()
    out = Path(out_dir)
    n = write_stl(assembled, out / "stage_assembled.stl", "stage_assembled")
    print(f"stage_assembled  {n:7d} tris")
    print(f"{'part':20s} {'tris':>7s}  {'footprint':>13s} {'height':>6s}  overhangs")
    for name, (m, up) in parts.items():
        pm = orient(m, up)
        ntri = write_stl(pm, out / "print" / f"{name}.stl", name)
        rep = check(m, up)
        ncomp = len(m.decompose())
        fp = "x".join(f"{v:.0f}" for v in rep.footprint)
        ov = ", ".join(f"{o.area:.0f}mm2 {o.size[0]:.0f}x{o.size[1]:.0f}"
                       f"@({o.center[0]:.0f},{o.center[1]:.0f},{o.center[2]:.0f})"
                       for o in rep.overhangs[:4]) or "none"
        warn = "" if ncomp == 1 else f"  !! {ncomp} pieces"
        warn += "" if rep.fits((220, 220)) else "  !! exceeds 220 bed"
        print(f"{name:20s} {ntri:7d}  {fp:>13s} {rep.height:6.0f}  {ov}"
              f"  (minor {rep.minor_area:.0f}mm2){warn}")


if __name__ == "__main__":
    main(*sys.argv[1:])
