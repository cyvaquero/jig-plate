# jig-plate

Purpose: A 3D generator for a stackable laser jig plate with magnet pockets
for marrying multiple plates and maintaining position on the laser bed. This
is the base plate to which pockets are added for various types and sizes of
blanks.

Parametric generator for the **base plate only** — no blank-specific pockets,
lips, or vents. `jig-plate.py` builds the plate and a corner test coupon
(for the stacking rib/groove joint) as binary STL using trimesh with the
manifold boolean engine, and renders diagrams and technical drawings with
matplotlib.

Only what is blank-agnostic lives here — magnet bores and the corner
stacking rib/groove system — so any pocket layout for any blank can be
built on top of this base without touching this geometry.

## Two files, two roles

- `jig_plate_base.py` — the importable library. `build_plate()` returns a
  `PlateResult` (`.solid`: the trimesh solid, `.geometry`: a `PlateGeometry`
  record of every magnet-bore and stacking-rib/groove position) with no
  file I/O, no argv, no printing. A blank-specific generator script imports
  this directly: `from jig_plate_base import build_plate`.
- `jig-plate.py` — the CLI entry point (argument parsing, STL export,
  diagrams). A hyphenated filename can't be `import`ed, which is exactly
  why the reusable geometry doesn't live here.

Keep this split: geometry and derived positions belong in
`jig_plate_base.py`; anything CLI-only (argparse, file writing, matplotlib
diagrams) belongs in `jig-plate.py`.

## Run

```bash
.venv/bin/python jig-plate.py
```

Writes STLs to `output/` and PNGs to `images/`, both gitignored. The script
prints `watertight: True` for both meshes — if either is `False`, the
geometry is broken and must not be released.

To use the plate from another generator script instead of running the CLI:

```python
from jig_plate_base import build_plate
result = build_plate()  # or build_plate(label="...", plate_x=..., ...)
result.solid             # trimesh.Trimesh
result.geometry.mag_xs   # reserved zones to lay pockets out around
```

Setup from scratch: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`

## Versioning — `major.minor.iterative`

`VERSION` in the script is the single source of truth. It drives the output
filenames and the 80-byte STL header (`head -c 80 file.stl`). Keep `version` in
`pyproject.toml` in sync.

- **iterative**: bump automatically on any change to the generated model —
  a change to the plate's default output (geometry, dimensions, positions)
  *or* a change to how the model is generated (parameters, CLI options,
  generation logic), even when the default output itself is unaffected.
  A default-output change is the clearer, more common case; do not treat
  the generation-logic clause as the only one that matters.
- **minor / major**: bump only when explicitly told to; zero the fields below it

Every iterative change gets an entry in the `Changelog` block of the script
docstring -- a short summary line, but with as many follow-up lines as needed
to name what changed, why, and what was verified; these have run to several
lines per entry in practice, not literally one line. `CHANGELOG.md` records
**major and minor releases only** — do not add iterative entries there; they
are folded into the next minor release.

## Git

git-flow: work on `develop`, releases via `release/x.y.z` merged to `main` and
tagged `vx.y.z`, then merged back to `develop`.

## Drawings

Alongside the mesh the script renders an isometric overview diagram and
dimensioned technical drawings (top plan, front elevation, and a detail sheet
carrying the magnet-bore and stacking-joint cross-sections). These are
documentation, not geometry: a drawing-only change bumps nothing and gets no
changelog entry.

- No view hand-tunes `set_xlim`/`set_ylim`. Most call `ax.autoscale_view()`
  plus `ax.margins()` directly; the two-panel detail sheet (magnet-bore and
  stacking-joint cross-sections, sharing one figure) uses `_fit_view` instead,
  since autoscaling each panel independently would give them different
  scales. Dimension labels are `ax.text`, which never reaches `dataLim`, so
  plain autoscaling crops them — that is what `_fit_view` corrects for, and
  why the margins the other views pass to `ax.margins()` need to be generous
  enough to leave room for their own dimension text.

## Design constraints that must not be regressed

- Magnet bores share X positions on the front and back faces and are symmetric
  about the X centreline so plates mate either way round.
- Plate must stay <= 246 mm in X (bed width plus purge-area clearance).
- Corner stacking ribs (top face) and grooves (bottom face) are positioned
  off `plate_x`/`plate_y` only, never off pocket or blank layout, so any two
  plates sharing this outer footprint stack together regardless of what
  pockets get added to each later.
- Nothing in this script may depend on a specific blank's dimensions. If a
  change references a card, part, or pocket size, it belongs in a
  blank-specific script layered on top of this one, not here.
