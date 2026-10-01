# Design notes

The brief for every model in this repo. Read this before starting a new design, and add to it when
something new is learned. Machine-readable values live in `modelkit/printer.py`.

## The workshop

* **Printer: Bambu Lab X1 Carbon.** The build volume is 256 × 256 × 256 mm. Design parts to fit
  ~250 mm, leaving a margin for the purge area and brims. The Star Theater was designed to fit 220 mm,
  so it never used the full bed.
* **Table: about 1 m × 2 m.** There's lots of room. Leave space at the edges for character sheets,
  rulebooks and dice.
  * Someday: a set that fills as much of the table as possible, with that space still left over.
    Ambitious; not a current goal.
* **Print time and filament are real costs.** The Star Theater is 20 parts, about 2.5 kg of PLA at
  15% infill, and 12+ plates of ~8 hours each. Getting finished parts off the bed will need some
  automation.
  * The build report's `~g` column estimates filament the way a slicer fills a part: a solid ~1 mm
    shell over every surface, plus sparse infill inside (`modelkit/printer.py`). Floors and decks
    are most of it: 1.6 of the theater's 2.5 kg.
  * **The best lever is slicer settings, not geometry.** Terrain needs very little strength.
    Dropping infill from 15% to 5% takes the theater from ~2.5 to ~1.9 kg. Bambu Studio's
    **Lightning** infill, which only holds up top surfaces, suits flat-topped floors even better.
  * **Hollowing floors from below barely helps on FDM.** It was measured on the theater's deck:
    vaulted channels removed ~45% of the solid volume but only ~7% of the filament, because the
    infill was already sparse and every rib adds solid walls. `modelkit/hollow.py` (supportless
    vaulted channels) is kept for resin prints, which print solid, and for high-infill FDM.
  * Every surface costs a solid shell, so lots of small detail adds up. Big plain areas are cheap.
  * Fewer, fuller plates beat many small ones. Lay out parts near 250 mm when the seams allow.

## Scale and gameplay

* **Scale:** ~32 mm heroic (Malifaux and D&D minis). 1 m in the world is about 18 mm.
* **Bases:** Malifaux uses 30, 40 and 50 mm round bases. Sizes that worked:
  * Doors at least 36 mm wide and 50 mm tall for 30 mm bases. Use 40 mm or wider where 40 mm bases
    should pass.
  * Standing spots at least 31 mm deep for a 30 mm base, or 41 mm for a 40 mm base.
  * Headroom of 50 mm or more under overhead structures, so models fit underneath and hands can reach.
* **What's fun on this table:**
  * **Verticality.** Elevated spots that models can actually stand on (opera boxes, balconies) were a
    favourite. Make them usable: a flat floor big enough for a base, open from above so a hand can
    place a model, and a vantage point over the rest of the board. Getting up there can be handwaved;
    ladders aren't required.
  * **Cover and difficult terrain.** Furniture that models stand on (rows of theatre seats) works
    well: "ducking behind the chairs." Keep such surfaces close to level. A tilt of about 10° across
    two rows was the compromise used.
  * **Fast lanes.** Wide aisles and clear routes give a quick way across, set against the slow
    cluttered areas.
  * **Separate areas with ways between them.** Doors and openings between areas (front of house and
    backstage, say) open up flanking routes.
  * **Theme in the details.** Character-specific touches (Colette's star motif, clockwork doves,
    playbills) are what make a set feel like a place.
* **Multi-piece sets:** pieces that face each other across the table, so they can be spread apart
  to make room.

## Printing conventions

These worked on the Star Theater; treat them as defaults.

* **Design for printing from the start.** Choose seams while designing, not afterwards with a
  splitting tool. Good seams change the geometry (see below), so they can't be found mechanically.
  * Put seams where they hide: under walls, on plank lines, at the foot of a step or riser, along a
    pilaster's edge.
  * Keep delicate features whole on one side of a seam.
* **Walls print lying down.** Split a wall lengthwise down its centre plane and print both halves
  with the cut face on the bed, decoration up.
  * Anything that hangs into an opening (curtains, valances, signs, finials) must reach back to the
    split plane, so nothing starts in mid-air.
  * A wall whose back is plain (facing the table edge) doesn't need splitting: print it on its back.
* **Delicate upright parts print separately, upright.** Balusters, railings and balconies print as
  their own parts in their natural orientation, then sit on brackets or columns built into the main
  pieces.
* **The 45° rule.** Anything that overhangs gets a 45° underside: corbels under balconies, cornice
  steps, column capitals. Bridges of up to ~30 mm are fine (canopy roofs, rails between balusters).
* **Alignment: 4.5 mm steel BBs** (".177 caliber" airgun BBs) in half-sphere pockets on both faces.
  * Use `modelkit.csg.ball_pocket()` centred on the seam. `BALL_D` sets the size.
  * Leave at least ~2 mm of material around a pocket, so faces need about 5 mm of depth.
  * Parts that should lift off (balconies) rest on BBs without glue.
* **Walls into floors:** a 2 mm tenon on the wall bottom drops into a slot in the floor, with
  0.2 mm clearance.
* **Fine detail:** about 1.2 mm minimum (0.8 mm grooves are fine). Relief text needs a cap height of
  4 mm or more.

## Workflow and tooling

* Each project script's `build()` returns the assembled model plus `{part: (manifold, up)}`.
  `export_parts` writes everything and prints the report.
* **Check every change:**
  * Each part decomposes to exactly one piece, so nothing floats.
  * The part volumes sum to the assembled volume.
  * Separately printed parts don't overlap the parts they sit on.
  * Pockets on mating parts line up.
  * The report shows no real overhangs and nothing too big for the bed.
* **Look at it:** render previews with `tools/render`, and publish an interactive three.js viewer
  (with an explode slider for the parts) when sharing a design.
* **Coordinates:** millimetres, Z up, +Y toward the viewer/audience. Seen from +Y, +X is on the
  viewer's **left**, so text on a face looking toward +Y must be mirrored
  (`text_section(..., mirror=True)`).

## Gotchas we hit

* **Mirrored lettering:** see the coordinates note above. Render text close up before trusting it.
* **Floating details:** a stem that stops short of the thing it holds up (finials, crest stars).
  The one-piece check catches it.
* **Order of operations:** cutting a recess after adding the detail that goes inside it erases the
  detail. Add inner details after the cut.
* **Extruding an empty 2D shape** used to produce an invalid solid that silently emptied the whole
  model. The `extrude_*` helpers now guard against it.
* **Decoration past the end of a piece:** frames and mouldings that stick out past a wall's end
  print over air. Trim decoration to the piece's outline.
