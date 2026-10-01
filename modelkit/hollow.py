"""Hollow out thick floors from underneath, without needing supports.

The cavities are parallel channels open at the bottom, each with a pointed,
steep-sided roof (steeper than 45 degrees, like a gothic vault), separated by
thin ribs. Every surface prints as an ordinary wall, so there's no bridging and
no support material, and the ribs carry the floor above.

When it pays off: resin printing (parts print solid, so hollowing saves a lot)
and FDM prints at high infill. At normal FDM settings (~15% sparse infill) it
barely helps: the slicer is already printing the inside sparse, and the new
ribs and channel walls each get solid perimeters. On the Star Theater's deck it
saved ~45% of solid volume but only ~7% of filament, so it isn't used there.
Lower infill or Lightning infill is the better lever for FDM terrain.
"""

from __future__ import annotations

from manifold3d import CrossSection, Manifold, OpType

from modelkit.csg import circle_pts, extrude_xy, extrude_xz, section, union

ROOF_RISE = 0.6   # roof height per unit of channel width: ~50 degrees from horizontal


def channels(plan: CrossSection, z_peak: float, width: float = 12.0, rib: float = 1.6,
             min_wall: float = 1.5) -> Manifold:
    """Cavity to subtract: channels running along Y under `plan`, roofs peaking at `z_peak`.

    `plan` is the region to hollow, already inset from the outside walls and with
    keep-out zones (pockets, slots, column feet...) removed. The channel width
    shrinks if the floor is too thin for a full one. Returns an empty Manifold if
    there's no room.
    """
    if plan.is_empty():
        return Manifold()
    # Fit the roof: rectangle up to z_wall, then the pointed roof to z_peak.
    w = min(width, (z_peak - min_wall) / ROOF_RISE)
    if w < 3.0:
        return Manifold()
    z_wall = z_peak - ROOF_RISE * w
    x0, y0, x1, y1 = plan.bounds()
    profiles = []
    x = x0
    while x < x1:
        profiles.append([(x, -1.0), (x + w, -1.0), (x + w, z_wall), (x + w / 2, z_peak), (x, z_wall)])
        x += w + rib
    prisms = union(extrude_xz(section(p), y0 - 1, y1 + 1) for p in profiles)
    return prisms ^ extrude_xy(plan, -2.0, z_peak + 1.0)


def discs(points: list[tuple[float, float]], r: float) -> CrossSection:
    """Round keep-out zones (e.g. around BB pockets or column feet)."""
    if not points:
        return CrossSection()
    return CrossSection.batch_boolean([section(circle_pts(x, y, r, 24)) for (x, y) in points],
                                      OpType.Add)
