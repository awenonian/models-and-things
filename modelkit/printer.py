"""The workshop: printer and table the models are designed for.

Keep this in sync with DESIGN_NOTES.md.
"""

# Bambu Lab X1 Carbon: 256 x 256 x 256 mm build volume. Parts are checked
# against BED_MARGIN so there's room for a brim and the purge area.
BED = (256.0, 256.0, 256.0)
BED_MARGIN = 6.0
USABLE_BED = tuple(v - BED_MARGIN for v in BED)

# Gaming table, about 1 m x 2 m. Leave room at the edges for character
# sheets, rulebooks and dice.
TABLE = (1000.0, 2000.0)

# Rough filament estimate: PLA density, and the fraction of a part's solid
# volume a typical slicer profile actually fills (walls + ~15% infill).
PLA_G_PER_CM3 = 1.24
FILL_FRACTION = 0.35
