# Notes for Claude

This repo makes 3D-printable tabletop terrain from Python (manifold3d). Before designing or changing
a model, read `DESIGN_NOTES.md`. It's the brief: printer and bed size, table size, scale and base
sizes, the gameplay the user enjoys, and the printing conventions to follow.

* Shared tools are in `modelkit/`; each model lives in `projects/<name>/` (see `README.md`).
* Run scripts from the repo root: `python -m projects.<name>.<script>`.
* After any change, rebuild and read the per-part report. Every part should be one piece, fit the
  bed and show no real overhangs. Render previews with `tools/render` and look at them.
* When something new is learned (a preference, a printing lesson, a gotcha), add it to
  `DESIGN_NOTES.md`.
