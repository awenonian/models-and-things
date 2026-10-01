"""The Star Theater -- stage piece.

Colette Du Bois' theater in Malifaux: a ritzy proscenium stage with a curved
apron out front, a proscenium wall standing across the middle of the base, and
a backstage area behind it. Two side doors and the main arch let models move
between front-of-house and backstage.

Run from the repo root:
    python -m terrain.star_theater.stage

Outputs (in output/star_theater/):
    stage_full.stl      everything, as one solid
    stage_platform.stl  the stage base + floor-level details
    stage_wall.stl      proscenium wall + all wall decoration (sits on z = STAGE_H)

Scale: ~32 mm "heroic" (Malifaux / D&D). 1 m in the world ~= 18 mm.
"""

from __future__ import annotations

import math
import random
import sys
import time
from pathlib import Path

from manifold3d import CrossSection, JoinType, Manifold

from terrain.common.csg import (
    box, circle_pts, cyl, ellipse, extrude_xy, extrude_xz, extrude_yz, gear_pts,
    revolve_profile, ring, section, segmental_arch_pts, sphere, star_pts,
    text_section, union, write_stl,
)

# ---------------------------------------------------------------------------
# Key dimensions (mm)
# ---------------------------------------------------------------------------

HALF_W = 200.0          # base is 400 mm wide (x = -200 .. 200)
STAGE_H = 20.0          # stage deck height above the table
WALL_T = 16.0           # proscenium wall thickness
WALL_FRONT = 0.0        # wall front face at y = 0; wall occupies y = -WALL_T .. 0
WALL_TOP = 190.0        # top of cornice
BACK_Y = -116.0         # back edge of the backstage area (100 mm of backstage)
APRON_SIDE_Y = 85.0     # apron front edge at the far left/right
APRON_MID_Y = 112.0     # apron front edge at centre (curved thrust)

OPEN_HW = 100.0         # proscenium opening half-width (200 mm wide)
OPEN_SPRING = 120.0     # z where the arch springs
OPEN_RISE = 30.0        # segmental arch rise -> crown at z = 150

DOOR_X = 160.0          # side door centre (mirrored)
DOOR_HW = 18.0          # 36 mm wide doors (fits a 30 mm base with room)
DOOR_SPRING = 57.0      # round-headed door -> top at 75

BOX_X0, BOX_X1 = 133.0, 187.0   # opera box extents (right side; mirrored)
BOX_FLOOR = 116.0
BOX_DEPTH = 28.0        # projection of the box floor in front of the wall
BOX_BOW = 6.0           # extra bulge of the bowed front

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
    body = extrude_xy(deck, 0.6, STAGE_H)
    # Small chamfer-ish foot to fight elephant's foot: slightly inset bottom.
    body += extrude_xy(deck.offset(-0.6, JoinType.Miter), 0.0, 0.6)

    # Nosing lip around the top edge and a plinth at the bottom.
    body += extrude_xy(ring(deck, 1.6, -1.0), STAGE_H - 2.5, STAGE_H)
    body += extrude_xy(ring(deck, 1.2, -1.0), 0.6, 3.5)
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
    x = -HALF_W + PLANK_W
    while x < HALF_W - 1:
        cuts.append(box(x - GROOVE_W / 2, x + GROOVE_W / 2, BACK_Y - 2, y_front, z0, z1))
        x += PLANK_W
    # butt joints
    for i in range(int(2 * HALF_W / PLANK_W) + 1):
        xa = -HALF_W + i * PLANK_W
        y = BACK_Y + rng.uniform(10, 70)
        while y < APRON_MID_Y:
            cuts.append(box(xa, xa + PLANK_W, y - GROOVE_W / 2, y + GROOVE_W / 2, z0, z1))
            y += rng.uniform(60, 110)
    return union(cuts)


TRAP_C = (0.0, 52.0)
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
    hood_outer = Manifold.sphere(4.2, 28)
    hood = hood_outer - Manifold.sphere(3.4, 28)
    hood = hood ^ box(-5, 5, 0, 5, 0, 5)           # quarter shell, open toward stage (-y)
    hood += box(-4.2, 4.2, -1.5, 4.2, -0.6, 0.6)     # base plate
    lamp = sphere(1.6, 0, 0.6, 1.6, 16) + cyl(0.9, 0, 1.2, 0, 0.6, segments=12)
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
    cab = box(-w / 2, w / 2, -d / 2, d / 2, 4, h)
    # Feet.
    for sx in (-1, 1):
        for sy in (-1, 1):
            cab += cyl(2.0, 0, 4.5, sx * (w / 2 - 3), sy * (d / 2 - 3), r_top=2.6, segments=16)
    # Crown moulding and dome.
    cab += box(-w / 2 - 1.5, w / 2 + 1.5, -d / 2 - 1.5, d / 2 + 1.5, h - 3, h)
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
        crate(22).rotate((0, 0, 14)).translate((-176, BACK_Y + 18, z + 26)),
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
        parts.append(pilaster(sx * 121.0))
    # Corner pilasters at the wall ends.
    for sx in (-1, 1):
        parts.append(box(sx * 191, sx * HALF_W, -0.1, 3.0, STAGE_H, WALL_TOP - 14))
        parts.append(box(sx * 190, sx * HALF_W, -0.1, 4.0, STAGE_H, STAGE_H + 9))
        parts.append(box(sx * 190, sx * HALF_W, -0.1, 4.5, WALL_TOP - 21, WALL_TOP - 14))
    return union(parts)


def pilaster(cx: float) -> Manifold:
    hw = 8.0
    z_top = WALL_TOP - 14
    p = box(cx - hw, cx + hw, -0.1, 4.0, STAGE_H, z_top)
    # Base: two stepped blocks.
    p += box(cx - hw - 2, cx + hw + 2, -0.1, 6.0, STAGE_H, STAGE_H + 7)
    p += box(cx - hw - 1, cx + hw + 1, -0.1, 5.0, STAGE_H + 7, STAGE_H + 10)
    # Capital: necking, echinus (45 deg flare -> printable), abacus.
    p += box(cx - hw - 0.5, cx + hw + 0.5, -0.1, 4.6, z_top - 13, z_top - 11)
    flare = section([(-0.1, z_top - 9), (4.6, z_top - 9), (7.0, z_top - 6.5),
                     (7.0, z_top), (-0.1, z_top)])
    p += extrude_yz(flare, cx - hw - 2.5, cx + hw + 2.5)
    # Volutes on the capital (little scroll discs).
    for sx in (-1, 1):
        vol = extrude_xz(section(circle_pts(cx + sx * (hw + 0.5), z_top - 6.5, 2.6, 20)), 3, 7.6)
        vol -= extrude_xz(section(circle_pts(cx + sx * (hw + 0.5), z_top - 6.5, 1.2, 16)), 7, 8)
        p += vol
    # Flutes.
    flutes = []
    for dx in (-4.2, 0, 4.2):
        fx = cx + dx
        groove = section([(fx - 0.9, STAGE_H + 14), (fx + 0.9, STAGE_H + 14),
                          (fx + 0.9, z_top - 17), (fx - 0.9, z_top - 17)]).offset(
            0.0)
        flutes.append(extrude_xz(groove, 2.8, 5))
        flutes.append(sphere(0.9, fx, 4.0, STAGE_H + 14, 10))
        flutes.append(sphere(0.9, fx, 4.0, z_top - 17, 10))
    p -= union(flutes)
    return p


def curtains() -> Manifold:
    """Tied-back main drapes inside the arch, with a swagged valance."""
    parts = []
    y_mid = -9.0
    # --- side drapes (build right one, mirror) ---
    jamb = OPEN_HW + 6.0          # buried into the jamb
    xs = []
    x = jamb
    inner_limit = OPEN_HW - 40
    while x > inner_limit:
        xs.append(x)
        x -= 0.7
    amp, lam, th = 2.0, 7.0, 1.6
    front = [(x, y_mid + amp * math.sin(2 * math.pi * x / lam) + th) for x in xs]
    back = [(x, y_mid + amp * math.sin(2 * math.pi * x / lam) - th) for x in reversed(xs)]
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
    drape = folds ^ extrude_xz(section(sil), -16, 0)
    # Puddle at the floor: slight flare in thickness.
    drape += extrude_xz(section([(OPEN_HW - 25, STAGE_H), (jamb, STAGE_H), (jamb, STAGE_H + 2.5),
                                 (OPEN_HW - 23.5, STAGE_H + 2.5)]), y_mid - 3.8, y_mid + 3.8)
    # Tie-back: a band round the drape + a tassel.
    band_x = OPEN_HW - 12.5
    band = box(band_x - 1, jamb, y_mid - 4.2, y_mid + 4.2, tie_z - 1.6, tie_z + 1.6)
    drape += band
    drape += cyl(1.6, tie_z - 9, tie_z - 1.5, band_x + 1.5, y_mid + 4.2, r_top=0.6, segments=14)
    drape += sphere(1.6, band_x + 1.5, y_mid + 4.2, tie_z - 1.6, 12)
    parts.append(both_sides(drape))

    # --- swagged valance ---
    crown = OPEN_SPRING + OPEN_RISE
    n_swags = 5
    sw = 2 * OPEN_HW / n_swags
    tiers = [(-6.5, -3.8, 128.0, 13.0), (-3.8, -1.8, 132.0, 8.5), (-1.8, -0.2, 136.0, 4.0)]
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
    # Tassels at the swag junctions.
    for i in range(1, n_swags):
        x = -OPEN_HW + i * sw
        parts.append(sphere(1.8, x, -1.2, 134.0, 12))
        parts.append(cyl(1.8, 124.0, 133.0, x, -1.2, r_top=0.8, segments=14))
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


def opera_box(sx: int) -> Manifold:
    """A bowed opera box above the side door (built for the right side, sx=+1)."""
    x0, x1 = BOX_X0, BOX_X1
    xc = (x0 + x1) / 2
    hw = (x1 - x0) / 2
    # Plan outline of the floor: rectangle + bowed front.
    bow = []
    for i in range(25):
        t = i / 24
        x = x0 + t * (x1 - x0)
        bow.append((x, BOX_DEPTH + BOX_BOW * math.sin(math.pi * t)))
    floor_cs = section([(x0, -2.0)] + bow + [(x1, -2.0)])
    floor_z = BOX_FLOOR
    floor = extrude_xy(floor_cs, floor_z - 3.5, floor_z)
    # Moulded edge band under the floor lip.
    floor += extrude_xy(floor_cs.offset(0.8), floor_z - 4.5, floor_z - 2.5)
    # Support: convex hull down to a thin strip on the wall -> ~45 deg underside.
    strip = box(DOOR_X - DOOR_HW - 4, DOOR_X + DOOR_HW + 4, -1.0, 0.0,
                floor_z - 37.0, floor_z - 36.0)
    support = (strip + extrude_xy(floor_cs, floor_z - 4.5, floor_z - 3.5)).hull()
    # Decorative ribs on the support (three corbels on the underside).
    m = floor + support
    for dx in (-hw + 6, 0, hw - 6):
        x = xc + dx
        ymax = BOX_DEPTH + BOX_BOW * math.sin(math.pi * (x - x0) / (x1 - x0))
        rib = section([(0, floor_z - 36), (0.8, floor_z - 37), (ymax + 1.0, floor_z - 4.5),
                       (ymax + 1.0, floor_z - 3.0), (0, floor_z - 3.0)])
        m += extrude_yz(rib, x - 1.6, x + 1.6)
        m += sphere(1.6, x, 1.0, floor_z - 36.0, 10)

    # Balustrade: top rail following the bow + turned balusters.
    rail_h = 13.0
    top_rail = extrude_xy(ring(section([(x0, -2.0)] + bow + [(x1, -2.0)]), 0.0, -2.6)
                          ^ section([(x0 - 5, 1.0), (x1 + 5, 1.0), (x1 + 5, 60), (x0 - 5, 60)]),
                          floor_z + rail_h - 2.2, floor_z + rail_h)
    m += top_rail
    m += extrude_xy(ring(floor_cs, 0.0, -2.0)
                    ^ section([(x0 - 5, 1.0), (x1 + 5, 1.0), (x1 + 5, 60), (x0 - 5, 60)]),
                    floor_z, floor_z + 1.6)
    baluster = revolve_profile([
        (0, 0), (1.25, 0), (1.25, 0.6), (0.7, 1.2), (0.75, 2.0), (1.35, 4.3), (1.1, 6.0),
        (0.6, 7.6), (0.6, 8.4), (1.0, 8.9), (1.0, 9.6), (0, 9.6),
    ], 14).scale((1, 1, (rail_h - 2.2 - 1.6) / 9.6))
    pts = []
    # Along the bow (skip ends; corners get posts).
    for i in range(1, 10):
        t = i / 10
        x = x0 + t * (x1 - x0)
        y = BOX_DEPTH + BOX_BOW * math.sin(math.pi * t) - 1.3
        pts.append((x, y))
    # Along the sides.
    for y in (8.0, 15.0, 22.0):
        pts.append((x0 + 1.3, y))
        pts.append((x1 - 1.3, y))
    for (x, y) in pts:
        m += baluster.translate((x, y, floor_z + 1.6))
    # Corner posts + slim columns up to the canopy.
    canopy_z0 = 158.0
    for x in (x0 + 1.8, x1 - 1.8):
        y = BOX_DEPTH - 1.5
        m += box(x - 1.9, x + 1.9, y - 1.9, y + 1.9, floor_z, floor_z + rail_h + 1)
        m += sphere(1.7, x, y, floor_z + rail_h + 1.6, 12)
        m += cyl(1.15, floor_z + rail_h, canopy_z0, x, y, segments=14)
    # Canopy: a valance board with a scalloped hem, roof slab, crest.
    cz1 = canopy_z0 + 9.0
    canopy_cs = section([(x0 - 2, -1.0), (x0 - 2, BOX_DEPTH + 1.5), (x1 + 2, BOX_DEPTH + 1.5),
                         (x1 + 2, -1.0)])
    roof = extrude_xy(canopy_cs, cz1, cz1 + 2.2)
    roof += extrude_xy(canopy_cs.offset(-1.5), cz1 + 2.2, cz1 + 3.4)
    hem = []
    for i in range(6):
        sxs = x0 - 2 + i * (x1 - x0 + 4) / 6
        swd = (x1 - x0 + 4) / 6
        for k in range(9):
            t = k / 8
            hem.append((sxs + t * swd, canopy_z0 - 3.5 * math.sin(math.pi * t)))
    hem += [(x1 + 2, cz1 + 0.5), (x0 - 2, cz1 + 0.5)]
    hem_cs = section(hem)
    roof += extrude_xz(hem_cs, BOX_DEPTH - 1.2, BOX_DEPTH + 1.2)
    # Side valances.
    side_hem = section([(-1, canopy_z0 + 1), (BOX_DEPTH + 1.2, canopy_z0 - 2),
                        (BOX_DEPTH + 1.2, cz1 + 0.5), (-1, cz1 + 0.5)])
    roof += extrude_yz(side_hem, x0 - 2, x0 - 0.2)
    roof += extrude_yz(side_hem, x1 + 0.2, x1 + 2)
    # Crest: a small star on top of the canopy front.
    roof += extrude_xz(section(star_pts(xc, cz1 + 8.5, 5.0)), BOX_DEPTH - 2.2, BOX_DEPTH - 0.4)
    roof += extrude_xz(section([(xc - 3, cz1 + 2), (xc + 3, cz1 + 2), (xc + 1.2, cz1 + 7.5),
                                (xc - 1.2, cz1 + 7.5)]), BOX_DEPTH - 2.4, BOX_DEPTH - 0.2)
    m += roof
    # Little drapes tied back inside the box opening.
    for side in (-1, 1):
        x_edge = x0 + 2.8 if side < 0 else x1 - 2.8
        sgn = 1 if side < 0 else -1
        drape = section([(x_edge, floor_z + rail_h), (x_edge + sgn * 3.0, floor_z + rail_h),
                         (x_edge + sgn * 2.2, floor_z + rail_h + 12),
                         (x_edge + sgn * 9.0, canopy_z0 - 1), (x_edge, canopy_z0 - 1)])
        m += extrude_xz(drape, BOX_DEPTH - 4.2, BOX_DEPTH - 2.8)
    if sx < 0:
        m = mirror_x(m)
    return m


def box_niches() -> Manifold:
    """Recesses cut into the wall behind each opera box."""
    out = []
    xc = (BOX_X0 + BOX_X1) / 2
    for sx in (-1, 1):
        cs = section([(sx * (BOX_X0 + 4), BOX_FLOOR - 0.5), (sx * (BOX_X1 - 4), BOX_FLOOR - 0.5)] +
                     ([(x * sx, z) for (x, z) in circle_pts(xc, 146.0, (BOX_X1 - BOX_X0) / 2 - 4,
                                                            24, 0, 180)]))
        out.append(extrude_xz(cs, -7.0, 1.0))
    return union(out)


def box_niche_trim() -> Manifold:
    out = []
    xc = (BOX_X0 + BOX_X1) / 2
    for sx in (-1, 1):
        cs = section([(sx * (BOX_X0 + 4), BOX_FLOOR - 0.5), (sx * (BOX_X1 - 4), BOX_FLOOR - 0.5)] +
                     ([(x * sx, z) for (x, z) in circle_pts(xc, 146.0, (BOX_X1 - BOX_X0) / 2 - 4,
                                                            24, 0, 180)]))
        trim = ring(cs, 2.2, 0) ^ section([(-500, BOX_FLOOR + 1), (500, BOX_FLOOR + 1),
                                           (500, 300), (-500, 300)])
        out.append(extrude_xz(trim, 0, 1.6))
    return union(out)


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


def marquee() -> Manifold:
    """'THE STAR' marquee crest, standing proud of the cornice over the arch."""
    z0, z1 = 164.0, 199.0
    hw = 56.0
    yf = 10.5                                   # front face of the board
    top = segmental_arch_pts(hw, z1 - 5, 7.0, 40)
    board_cs = section([(-hw, z0), (hw, z0)] + top)
    m = extrude_xz(board_cs, -6.0, yf)
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
        m += extrude_xz(sc, -6.0, yf - 1.5)
        m += extrude_xz(section(circle_pts(sx * (hw + 9.5), z0 + 13.5, 3.4, 20)), yf - 2, yf + 0.4)
        m -= extrude_xz(section(circle_pts(sx * (hw + 9.5), z0 + 13.5, 1.4, 16)), yf - 0.6, yf + 1)
    # Star finial.
    crest_z = z1 + 2.0
    m += extrude_xz(section(star_pts(0, crest_z + 9, 9.0)), -2.0, 2.0)
    m += extrude_xz(section(star_pts(0, crest_z + 9, 5.5)), 1.5, 3.4)
    m += extrude_xz(section([(-5, z1 - 1), (5, z1 - 1), (2.5, crest_z + 6.0),
                             (-2.5, crest_z + 6.0)]), -3.0, 3.0)
    return m


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
    w += opera_box(1) + opera_box(-1)
    w += marquee()
    for sx in (-1, 1):
        w += dove(sx * 88.0, 151.0, 28.0, -sx, 0.0)
    # Back of the arch: simple frame on the backstage side.
    w += extrude_xz(ring(opening_outline(), 4.0, 0) ^ above_deck_xz(), -WALL_T - 2.6, -WALL_T)
    # Pin rail with belaying pins on the back of the wall (stage right).
    w += pin_rail()
    return w


def pin_rail() -> Manifold:
    parts = [box(-190, -120, -WALL_T - 7, -WALL_T, 84, 89)]
    for x in range(-186, -122, 7):
        parts.append(cyl(1.0, 78, 95, x, -WALL_T - 4.0, segments=10))
        parts.append(sphere(1.4, x, -WALL_T - 4.0, 95, 10))
    # Supporting brackets (45 deg, printable).
    for x in (-185, -125):
        br = section([(-WALL_T, 72), (-WALL_T, 84), (-WALL_T - 7, 84), (-WALL_T - 1, 72)])
        parts.append(extrude_yz(br, x - 1.5, x + 1.5))
    # Coiled ropes hanging off some of the pins.
    for x in (-179, -158, -137):
        coil = Manifold.revolve(section(circle_pts(4.0, 0, 0.9, 10)), 20)
        coil = coil.scale((1, 1, 1)).rotate((90, 0, 0)).scale((0.8, 1, 1.6))
        parts.append(coil.translate((x, -WALL_T - 4.0, 80)))
    return union(parts)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def build() -> dict[str, Manifold]:
    t0 = time.time()
    platform = build_platform()
    platform += backstage_props()
    print(f"  platform built in {time.time() - t0:.1f}s", file=sys.stderr)
    t0 = time.time()
    wall = build_wall()
    print(f"  wall built in {time.time() - t0:.1f}s", file=sys.stderr)
    full = platform + wall
    return {"stage_full": full, "stage_platform": platform, "stage_wall": wall}


def main(out_dir: str = "output/star_theater") -> None:
    parts = build()
    for name, m in parts.items():
        out = Path(out_dir) / f"{name}.stl"
        ntri = write_stl(m, out, name)
        bb = m.bounding_box()
        print(f"{name:16s} {ntri:8d} tris  genus={m.genus():4d}  "
              f"bbox=({bb[3]-bb[0]:.0f} x {bb[4]-bb[1]:.0f} x {bb[5]-bb[2]:.0f}) mm  -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:])
