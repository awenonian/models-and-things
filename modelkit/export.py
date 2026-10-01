"""Write a project's parts to STL in print orientation, with a printability report."""

from __future__ import annotations

from pathlib import Path

from manifold3d import Manifold

from modelkit.csg import write_stl
from modelkit.printcheck import check, orient
from modelkit.printer import FILL_FRACTION, PLA_G_PER_CM3, USABLE_BED

Parts = dict[str, tuple[Manifold, tuple[float, float, float]]]


def export_parts(assembled: Manifold, parts: Parts, out_dir: str | Path, name: str) -> None:
    """Write `<name>_assembled.stl` plus `print/<part>.stl` for each part (rotated so
    its `up` is +Z, resting on z = 0), and print one report line per part:
    triangles, footprint, height, solid volume, rough filament, overhangs, and
    warnings for parts that fall apart into pieces or don't fit the bed."""
    out = Path(out_dir)
    n = write_stl(assembled, out / f"{name}_assembled.stl", f"{name}_assembled")
    print(f"{name}_assembled  {n} tris")
    print(f"{'part':26s} {'tris':>7s} {'footprint':>9s} {'ht':>4s} {'cm3':>5s} {'~g':>4s}  overhangs")
    total_g = 0.0
    for pname, (m, up) in parts.items():
        ntri = write_stl(orient(m, up), out / "print" / f"{pname}.stl", pname)
        rep = check(m, up)
        cm3 = m.volume() / 1000.0
        grams = cm3 * FILL_FRACTION * PLA_G_PER_CM3
        total_g += grams
        fp = "x".join(f"{v:.0f}" for v in rep.footprint)
        ov = ", ".join(f"{o.area:.0f}mm2 {o.size[0]:.0f}x{o.size[1]:.0f}"
                       f"@({o.center[0]:.0f},{o.center[1]:.0f},{o.center[2]:.0f})"
                       for o in rep.overhangs[:3]) or "none"
        warn = "" if len(m.decompose()) == 1 else f"  !! {len(m.decompose())} pieces"
        if not rep.fits(USABLE_BED[:2]) or rep.height > USABLE_BED[2]:
            warn += "  !! too big for the bed"
        print(f"{pname:26s} {ntri:7d} {fp:>9s} {rep.height:4.0f} {cm3:5.0f} {grams:4.0f}  {ov}"
              f"  (minor {rep.minor_area:.0f}mm2){warn}")
    print(f"{'total':26s} {'':7s} {'':9s} {'':4s} {'':5s} {total_g:4.0f}  "
          f"(~{total_g / 1000:.1f} kg PLA, rough)")
