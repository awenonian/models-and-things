# models-and-things

3D-printable models generated from code: tabletop terrain for miniature wargames and D&D, built with
Python and [manifold3d](https://github.com/elalish/manifold).

Each model is a Python script. It builds the geometry with boolean modelling (CSG), splits it into
parts designed around how they print, checks every part for overhangs and bed fit, and writes STLs
already rotated for the slicer.

## Projects

| Project | What it is |
|---|---|
| [The Star Theater](projects/star_theater/) | Colette Du Bois' theater from Malifaux: a proscenium stage with opera boxes, an orchestra pit and backstage, facing raked seating with a balcony. 20 parts. |

![The Star Theater](projects/star_theater/images/theater_scene2.png)

## Layout

```
modelkit/            shared tools for every project
  csg.py             geometry helpers: extrusions, mouldings, arches, stars, text, BB pockets, STL export
  printcheck.py      overhang / bed-fit check, and rotation into print orientation
  export.py          writes a project's parts + the per-part printability report
  printer.py         the printer and table we design for (bed size, filament estimate)
  hollow.py          supportless vaulted channels for hollowing thick parts (mainly for resin)
  layout.py          lays print parts out on one "plate" for preview images
tools/render/        headless three.js renderer for preview PNGs
projects/<name>/     one folder per model: code, README, images/, output/ (generated STLs)
DESIGN_NOTES.md      the brief for new designs: printer, table, scale, gameplay, print conventions
```

## Setup

```sh
pip install -r requirements.txt
python -m projects.star_theater.stage       # run any project script from the repo root
```

Preview renders are optional. They use Node with Playwright and Chromium:

```sh
(cd tools/render && npm install)
node tools/render/render.mjs projects/star_theater/output/stage_assembled.stl /tmp/stage hero front
python -m modelkit.layout projects/star_theater/output/print /tmp/plate.stl   # all parts on one plate
node tools/render/render.mjs /tmp/plate.stl /tmp/plate plate
```

Camera views are named presets in `tools/render/render.mjs`; add new ones there for each project.

## Starting a new project

1. Read [DESIGN_NOTES.md](DESIGN_NOTES.md). It covers the printer, the table, scale, what makes terrain
   fun to play on, and the printing conventions that worked.
2. Make `projects/<name>/` with an empty `__init__.py`, and a script whose `build()` returns
   `(assembled, {part_name: (manifold, up_vector)})`. Its `main()` calls
   `modelkit.export.export_parts(*build(), OUT_DIR, "<name>")`. Use
   `projects/star_theater/stage.py` as the model.
3. Run it, fix anything the report flags, render previews, and write the project README.
