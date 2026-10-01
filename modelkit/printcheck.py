"""Printability checks: overhangs and bed fit for a part in its print orientation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from manifold3d import Manifold


@dataclass
class Overhang:
    area: float              # mm^2 of downward-facing surface
    size: tuple[float, float]  # horizontal extent (print frame), mm
    height: float            # height above the bed, mm
    center: tuple[float, float, float]  # model coordinates


@dataclass
class Report:
    footprint: tuple[float, float]   # print-frame X/Y extent, mm
    height: float                    # print-frame Z extent, mm
    overhangs: list[Overhang] = field(default_factory=list)
    minor_area: float = 0.0          # area of overhangs too small to matter

    def fits(self, bed: tuple[float, float]) -> bool:
        a, b = sorted(self.footprint)
        c, d = sorted(bed)
        return a <= c and b <= d


def _basis(up: tuple[float, float, float]):
    u = np.asarray(up, float)
    u /= np.linalg.norm(u)
    helper = np.array([1.0, 0, 0]) if abs(u[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = helper - u * np.dot(helper, u)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    return e1, e2, u


def check(m: Manifold, up: tuple[float, float, float], max_angle: float = 45.0,
          min_size: float = 1.2, min_area: float = 2.0) -> Report:
    """Find unsupported down-facing surfaces when printed with `up` pointing up.

    A face counts as an overhang when it tilts more than `max_angle` degrees
    from vertical and isn't resting on the bed. Connected regions that are
    narrower than `min_size` (mm) in either direction, or smaller than
    `min_area`, are folded into `minor_area`. Those are fine details printers
    handle without help: sphere undersides, 1 mm lips and similar. Bridges
    between supports (e.g. a rail across balusters) are reported too; judge
    those by their span.
    """
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(float)
    t = np.asarray(mesh.tri_verts, dtype=np.int64)
    e1, e2, u = _basis(up)
    h = v @ u
    h0 = h.min()

    p0, p1, p2 = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    cr = np.cross(p1 - p0, p2 - p0)
    area = 0.5 * np.linalg.norm(cr, axis=1)
    n = cr / np.maximum(2 * area, 1e-12)[:, None]
    thresh = -math.cos(math.radians(max_angle))
    on_bed = h[t].max(axis=1) < h0 + 0.05
    flagged = np.nonzero((n @ u < thresh) & ~on_bed & (area > 1e-9))[0]

    # Cluster flagged triangles that share vertices (union-find).
    parent = {int(i): int(i) for i in flagged}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    owner: dict[int, int] = {}
    for ti in flagged:
        for vi in t[ti]:
            vi = int(vi)
            if vi in owner:
                ra, rb = find(owner[vi]), find(int(ti))
                if ra != rb:
                    parent[ra] = rb
            else:
                owner[vi] = int(ti)
    groups: dict[int, list[int]] = {}
    for ti in flagged:
        groups.setdefault(find(int(ti)), []).append(int(ti))

    pts = np.stack([v @ e1, v @ e2, h - h0], axis=1)
    ext = pts.max(axis=0) - pts.min(axis=0)
    rep = Report(footprint=(float(ext[0]), float(ext[1])), height=float(ext[2]))
    for tris in groups.values():
        vid = np.unique(t[tris].ravel())
        q = pts[vid]
        size = q[:, :2].max(axis=0) - q[:, :2].min(axis=0)
        a = float(area[tris].sum())
        # Long thin bands (lips, steps) show up with a big bounding box; their
        # true width is roughly area / length.
        width = min(min(size), a / max(max(size), 1e-9))
        if width < min_size or a < min_area:
            rep.minor_area += a
            continue
        c = v[vid].mean(axis=0)
        rep.overhangs.append(Overhang(a, (float(size[0]), float(size[1])),
                                      float(q[:, 2].min()), tuple(np.round(c, 1))))
    rep.overhangs.sort(key=lambda o: -o.area)
    return rep


def orient(m: Manifold, up: tuple[float, float, float]) -> Manifold:
    """Rotate `m` so `up` points to +Z, then centre it on the origin, resting on z = 0."""
    u = np.asarray(up, float)
    u /= np.linalg.norm(u)
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(u, z)
    c = float(np.dot(u, z))
    if np.linalg.norm(v) < 1e-9:
        r = np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        r = np.eye(3) + vx + vx @ vx * (1 / (1 + c))
    m = m.transform(np.hstack([r, np.zeros((3, 1))]))
    bb = m.bounding_box()
    return m.translate((-(bb[0] + bb[3]) / 2, -(bb[1] + bb[4]) / 2, -bb[2]))
