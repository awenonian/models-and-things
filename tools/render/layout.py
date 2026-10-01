"""Lay the print-ready parts out in a grid (one STL) for a 'print plate' preview."""
import sys
from pathlib import Path

from manifold3d import Manifold

from terrain.common.csg import union, write_stl


def read_stl(path):
    import numpy as np
    from manifold3d import Mesh
    data = Path(path).read_bytes()
    n = int.from_bytes(data[80:84], "little")
    rec = np.frombuffer(data[84:84 + n * 50], dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    v = rec["v"].reshape(-1, 3)
    uniq, inv = np.unique(v, axis=0, return_inverse=True)
    return Manifold(Mesh(vert_properties=uniq.astype(np.float32), tri_verts=inv.reshape(-1, 3).astype(np.uint32)))


def main(src_dir, out, cols=4, gap=25.0):
    files = sorted(Path(src_dir).glob("*.stl"))
    placed, x, y, row_h, col = [], 0.0, 0.0, 0.0, 0
    for f in files:
        m = read_stl(f)
        bb = m.bounding_box()
        w, d = bb[3] - bb[0], bb[4] - bb[1]
        placed.append(m.translate((x - bb[0], y - bb[1], -bb[2])))
        x += w + gap
        row_h = max(row_h, d)
        col += 1
        if col == cols:
            x, y, row_h, col = 0.0, y - row_h - gap, 0.0, 0
            y = y  # rows go toward -y
    write_stl(union(placed), out, "layout")


if __name__ == "__main__":
    main(*sys.argv[1:])
