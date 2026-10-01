# models-and-things

3D-printable models generated from code (Python + [manifold3d](https://github.com/elalish/manifold)).

## The Star Theater (Malifaux)

Colette Du Bois' Star Theater, as tabletop terrain for Malifaux / D&D at ~32 mm heroic scale.
The battle map comes in two halves that face each other across the table:

1. **The stage** (this piece, done): `terrain/star_theater/stage.py`
2. **The seating** (coming next)

![Stage, hero view](docs/star_theater/stage_hero.png)

| Front | Backstage |
|---|---|
| ![front](docs/star_theater/stage_front.png) | ![back](docs/star_theater/stage_back.png) |
| ![arch](docs/star_theater/stage_arch.png) | ![box](docs/star_theater/stage_box.png) |

### What's on it

* **Stage base:** 400 × ~230 mm, 20 mm tall. The planked floor has staggered butt joints. A curved
  apron extends ~110 mm in front of the wall, with recessed skirt panels, a star medallion,
  shell-hooded footlights and a magician's trapdoor marked with a star. Three steps lead down
  from each front corner.
* **Proscenium wall:** 16 mm thick and 170 mm above the deck, standing across the middle of the base.
  * The segmental arch opening is 200 mm wide and ~130 mm tall. It has a stepped moulding, a
    keystone, fluted pilasters, a dentil cornice, tied-back main drapes and a swagged valance
    with tassels.
  * The **"THE STAR"** marquee rises above the cornice, ringed with bulbs and topped with a star.
    Two of Colette's clockwork doves sit in relief on either side of it.
  * Each side wall has a bowed **opera box** with turned balusters, columns and a scalloped
    canopy, set in an arched niche.
  * Under each box, a **36 mm door** leads backstage, so 30 mm bases fit through.
* **Backstage:** ~100 mm deep behind the wall. The back of the wall shows its timber framing
  and has a pin rail with coiled ropes. Props include stacked crates, a costume trunk and an
  illusionist's cabinet.

### Files

`python -m terrain.star_theater.stage` writes these to `output/star_theater/`:

| File | Contents |
|---|---|
| `stage_full.stl` | everything as one solid |
| `stage_platform.stl` | the base + floor-level details and props |
| `stage_wall.stl` | the proscenium wall and everything on it; its underside sits flat at z = 20 mm, on top of the deck |

All three are single connected manifold solids. Nothing floats.

### Printing notes

* Every piece is bigger than a typical print bed. The plan is to cut them with a separate
  splitting tool that adds alignment keys. That tool hasn't been written yet.
* Overhangs on the wall were designed for printing upright. The opera box undersides and the
  marquee have ~45° supports, and the cornice steps out at 45°.
* These still need supports when printed upright: the hanging valance swags and tassels (their
  low points start in mid-air), and the box canopy roofs (a ~28 mm bridge).
* The finest details are about 1.2 mm (baluster necks, floor grooves). They suit resin or a
  0.4 mm nozzle.

### Coordinates / conventions

Units are millimetres. X runs left/right and Z is up. **+Y points toward the audience.** The wall's
front face is at y = 0, the apron is at +Y and backstage is at −Y. Viewed from the audience, +X is
on the viewer's *left*, so text on front-facing surfaces is mirrored in code
(`text_section(..., mirror=True)`).

## Development

```sh
pip install -r requirements.txt
python -m terrain.star_theater.stage          # build STLs (~1 s)

# optional: preview renders (headless Chromium via Playwright + three.js)
(cd tools/render && npm install)
node tools/render/render.mjs output/star_theater/stage_full.stl docs/star_theater/stage hero front back
```

Shared CSG helpers live in `terrain/common/csg.py`. They cover extrusion in each principal
plane, offset rings for mouldings, stars, gears, segmental arches, text outlines and binary
STL export.
