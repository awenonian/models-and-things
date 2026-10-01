"""Small helper layer over manifold3d for building printable terrain.

Conventions used throughout the terrain models:
  * Units are millimetres.
  * X runs left/right, Y runs front/back (+Y is toward the audience / viewer),
    Z is up. The tabletop is at Z = 0.
"""

from __future__ import annotations

import math
import struct
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from manifold3d import CrossSection, FillRule, JoinType, Manifold

Point = tuple[float, float]

# ---------------------------------------------------------------------------
# Primitive construction
# ---------------------------------------------------------------------------


def box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Manifold:
    """Axis-aligned box from min/max extents (order of each pair doesn't matter)."""
    xa, xb = sorted((x0, x1))
    ya, yb = sorted((y0, y1))
    za, zb = sorted((z0, z1))
    return Manifold.cube((xb - xa, yb - ya, zb - za)).translate((xa, ya, za))


def cyl(r: float, z0: float, z1: float, x: float = 0.0, y: float = 0.0,
        r_top: float | None = None, segments: int = 32) -> Manifold:
    """Vertical cylinder (or cone frustum) standing on z0."""
    rt = r if r_top is None else r_top
    return Manifold.cylinder(z1 - z0, r, rt, segments).translate((x, y, z0))


def sphere(r: float, x: float = 0.0, y: float = 0.0, z: float = 0.0,
           segments: int = 24) -> Manifold:
    return Manifold.sphere(r, segments).translate((x, y, z))


def union(parts: Iterable[Manifold]) -> Manifold:
    parts = [p for p in parts if p is not None and not p.is_empty()]
    if not parts:
        return Manifold()
    if len(parts) == 1:
        return parts[0]
    return Manifold.batch_boolean(parts, _op("Add"))


def _op(name: str):
    from manifold3d import OpType
    return getattr(OpType, name)


def section(polys: Sequence[Sequence[Point]] | Sequence[Point],
            fill: str = "positive") -> CrossSection:
    """CrossSection from one polygon or a list of polygons.

    Polygons are auto-oriented so callers don't need to care about winding
    when using the default 'positive' rule on simple shapes.
    """
    if len(polys) and isinstance(polys[0][0], (int, float, np.floating)):
        polys = [polys]  # single polygon
    fixed = []
    for p in polys:
        arr = np.asarray(p, dtype=float)
        if fill == "positive" and _signed_area(arr) < 0:
            arr = arr[::-1]
        fixed.append(arr)
    rule = FillRule.EvenOdd if fill == "evenodd" else FillRule.Positive
    return CrossSection(fixed, rule)


def _signed_area(arr: np.ndarray) -> float:
    x, y = arr[:, 0], arr[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


# ---------------------------------------------------------------------------
# Extrusion in the three principal planes
# ---------------------------------------------------------------------------


def extrude_xy(cs: CrossSection, z0: float, z1: float) -> Manifold:
    """Plan-view shape (x, y) extruded upward from z0 to z1."""
    if cs.is_empty():
        return Manifold()
    return Manifold.extrude(cs, z1 - z0).translate((0, 0, z0))


def extrude_xz(cs: CrossSection, y0: float, y1: float) -> Manifold:
    """Front-elevation shape (x, z) extruded along Y from y0 to y1."""
    if cs.is_empty():
        return Manifold()
    ya, yb = sorted((y0, y1))
    m = Manifold.extrude(cs, yb - ya)
    # (a, b, c) -> (a, -c, b): a proper rotation, keeps normals outward.
    m = m.transform(np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0]], dtype=float))
    return m.translate((0, yb, 0))


def extrude_yz(cs: CrossSection, x0: float, x1: float) -> Manifold:
    """Side-elevation profile (y, z) extruded along X from x0 to x1."""
    if cs.is_empty():
        return Manifold()
    xa, xb = sorted((x0, x1))
    m = Manifold.extrude(cs, xb - xa)
    # (a, b, c) -> (c, a, b): cyclic permutation, a proper rotation.
    m = m.transform(np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]], dtype=float))
    return m.translate((xa, 0, 0))


def revolve_profile(profile: Sequence[Point], segments: int = 24) -> Manifold:
    """Lathe a (radius, z) profile around the Z axis (balusters, finials...)."""
    return Manifold.revolve(section(profile), segments)


# ---------------------------------------------------------------------------
# 2D shape helpers
# ---------------------------------------------------------------------------


def circle_pts(cx: float, cy: float, r: float, n: int = 48,
               a0: float = 0.0, a1: float = 360.0) -> list[Point]:
    """Points along a circular arc, inclusive of both ends (degrees)."""
    out = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def ellipse(cx: float, cy: float, rx: float, ry: float, n: int = 40) -> CrossSection:
    pts = [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n))
           for i in range(n)]
    return section(pts)


def star_pts(cx: float, cy: float, r_out: float, r_in: float | None = None,
             points: int = 5, rot_deg: float = 90.0) -> list[Point]:
    r_in = r_out * 0.42 if r_in is None else r_in
    pts = []
    for i in range(points * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rot_deg + i * 180.0 / points)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def gear_pts(cx: float, cy: float, r: float, teeth: int = 10,
             tooth_h: float | None = None) -> list[Point]:
    tooth_h = r * 0.22 if tooth_h is None else tooth_h
    pts = []
    n = teeth * 4
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r + (tooth_h if (i % 4) in (1, 2) else 0.0)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def segmental_arch_pts(half_w: float, spring_z: float, rise: float,
                       n: int = 40) -> list[Point]:
    """Points across a segmental arch from (+half_w, spring_z) to (-half_w, spring_z)."""
    r = (half_w ** 2 + rise ** 2) / (2 * rise)
    cz = spring_z + rise - r
    a = math.degrees(math.asin(half_w / r))
    return circle_pts(0.0, cz, r, n, 90 - a, 90 + a)


def text_section(text: str, height: float, cx: float = 0.0, cy: float = 0.0,
                 family: str = "DejaVu Serif", weight: str = "bold",
                 spacing: float = 0.0, mirror: bool = False) -> CrossSection:
    """Vector outline of a text string, cap-height ~= `height`, centred on (cx, cy).

    With +Y toward the viewer, a face seen from the front has +X on the viewer's
    left, so text on front-facing (x, z) elevations needs ``mirror=True``."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath

    fp = FontProperties(family=family, weight=weight)
    polys: list[np.ndarray] = []
    x_cursor = 0.0
    chars = list(text) if spacing else [text]
    for ch in chars:
        if not ch.strip():
            x_cursor += 0.35 + spacing
            continue
        tp = TextPath((x_cursor, 0), ch, size=1.0, prop=fp)
        for p in tp.to_polygons(closed_only=True):
            if len(p) >= 3:
                polys.append(np.asarray(p[:-1] if np.allclose(p[0], p[-1]) else p))
        ext = tp.get_extents()
        x_cursor = ext.x1 + spacing
    cs = CrossSection(polys, FillRule.EvenOdd)
    (x0, y0, x1, y1) = cs.bounds()
    s = height / max(y1 - y0, 1e-9)
    cs = cs.translate((-(x0 + x1) / 2, -(y0 + y1) / 2)).scale((-s if mirror else s, s))
    return cs.translate((cx, cy))


def ring(cs: CrossSection, outer: float, inner: float) -> CrossSection:
    """Band between two offsets of an outline (outer > inner, can be negative)."""
    return cs.offset(outer, JoinType.Round, 2.0, 48) - cs.offset(inner, JoinType.Round, 2.0, 48)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def write_stl(m: Manifold, path: str | Path, name: str = "model") -> int:
    """Write a binary STL. Returns triangle count."""
    mesh = m.to_mesh()
    verts = np.asarray(mesh.vert_properties)[:, :3].astype(np.float32)
    tris = np.asarray(mesh.tri_verts, dtype=np.int64)
    v0, v1, v2 = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    normals = np.cross(v1 - v0, v2 - v0)
    lens = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = (normals / np.where(lens == 0, 1, lens)).astype(np.float32)

    rec = np.zeros(len(tris), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"] = normals
    rec["v"] = np.stack([v0, v1, v2], axis=1)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        header = name.encode("ascii", "replace")[:80].ljust(80, b" ")
        f.write(header)
        f.write(struct.pack("<I", len(tris)))
        f.write(rec.tobytes())
    return len(tris)


# ---------------------------------------------------------------------------
# Joinery
# ---------------------------------------------------------------------------

# Alignment balls: .177 cal copper-plated steel airgun BBs (nominally 4.5 mm,
# real ones run ~4.35-4.5 mm). Each mating face gets a hemispherical pocket.
BALL_D = 4.5
BALL_CLEARANCE = 0.2   # added to the pocket diameter


def ball_pocket(x: float, y: float, z: float) -> Manifold:
    """A sphere centred on a seam: subtracting it leaves a half-pocket on each side."""
    return sphere((BALL_D + BALL_CLEARANCE) / 2, x, y, z, 28)
