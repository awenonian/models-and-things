"""Both halves of the Star Theater set out facing each other, for previews.

    python -m terrain.star_theater.scene [gap_mm]

Writes output/star_theater/theater_scene.stl: the stage, then the seating
`gap_mm` (default 150) in front of the apron.
"""

import sys
from pathlib import Path

from terrain.common.csg import write_stl
from terrain.star_theater import seating, stage


def main(gap: str = "150", out_dir: str = "output/star_theater") -> None:
    st, _ = stage.build()
    se, _ = seating.build()
    front = st.bounding_box()[4]
    scene = st + se.translate((0, front + float(gap), 0))
    n = write_stl(scene, Path(out_dir) / "theater_scene.stl", "theater_scene")
    print(f"theater_scene {n} tris")


if __name__ == "__main__":
    main(*sys.argv[1:])
