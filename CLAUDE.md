# jig-plate

Parametric generator for the **base plate** of a stackable laser jig: magnet
bores for marrying plates and holding position on the laser bed, plus a
corner stacking rib/groove system. No blank-specific pockets, lips or vents;
those are added on top of this base by blank-specific scripts.
`jig-plate.py` builds the plate and a corner test coupon (for the stacking
joint) as binary STL with trimesh and the manifold boolean engine, and
renders diagrams and technical drawings with matplotlib.

The global rules in `~/.claude/CLAUDE.md` and its skills apply in full;
this file holds only what is specific to this repo.

## Two files, two roles

- `jig_plate_base.py` — the importable library. `build_plate()` returns a
  `PlateResult` (`.solid`: the trimesh solid, `.geometry`: a `PlateGeometry`
  record of every magnet-bore and stacking-rib/groove position) with no
  file I/O, no argv, no printing.
- `jig-plate.py` — the CLI entry point (argparse, STL export, diagrams). A
  hyphenated filename can't be `import`ed, which is why the reusable
  geometry doesn't live here.

Geometry and derived positions belong in `jig_plate_base.py`; anything
CLI-only belongs in `jig-plate.py`.

## Run

```bash
.venv/bin/python jig-plate.py
```

Writes STLs to `output/` and PNGs to `images/`, both gitignored. The script
prints one line per mesh, `plate` and `stack coupon`, each with
`watertight: True` plus volume, bbox and face count. If either is `False`,
the geometry is broken and must not be released (the script then also
exits 1, after still writing the files).

From another generator script:

```python
from jig_plate_base import build_plate
result = build_plate()  # or build_plate(printer="h2d", label="...")
result.solid             # trimesh.Trimesh
result.geometry.mag_xs   # reserved zones to lay pockets out around
```

Setup: `python3.14 -m venv .venv && .venv/bin/pip install --require-hashes -r requirements.lock`
(`requirements.txt` is the loose input; regenerate the lock with
`pip-compile --generate-hashes --output-file requirements.lock requirements.txt`.)

## Versioning

`VERSION` in `jig-plate.py` is the single source of truth; keep `version` in
`pyproject.toml` in sync. It drives the output filenames and the 80-byte STL
header (`head -c 80 file.stl`), so release-branch builds carry the iterative
version until the `X.Y.0` bump just before the merge into `main`.

Besides the `CHANGELOG.md` entry, keep the `Changelog` block of the script
docstring in step: a summary line plus follow-up lines naming what changed,
why, and what was verified.

## Verified output formats

These stay byte-for-byte identical unless a change is meant to alter them.
Run the CLI before and after every change and report the comparison.

- `output/jig_plate_<VERSION>.stl` and `..._stack_coupon.stl`: binary STL,
  80-byte NUL-padded header starting `Jig plate <VERSION>`; both meshes
  watertight. A bump changes only filename and header (`cmp -i 80`). With
  `--printer P` (alias resolved) `_<P>` joins every name, `<P> | ` the header.
- `images/*.png`: the isometric diagram and three technical-drawing sheets.
  Compare visually; matplotlib PNGs aren't byte-stable across versions.
- `build_plate()` return shape: `PlateResult(solid, geometry)` and the
  `PlateGeometry` fields that blank-specific generators import.

## Git

- Older tags (`v0.1.0` to `v3.0.0`) carry a `v` prefix and stay as they
  are. There is no `RELEASING.md`.
- The default branch is `main`, so PRs into `develop` or a release branch
  don't auto-close issues; close those by hand.

## Blind review scope

There is no UI. The accessibility reviewer covers the docs (README images
need text alternatives), the CLI output and the generated drawings
(legibility, use of color, label contrast). Drawing code in `jig-plate.py`
and CLI output count as text shown to readers: a change to either runs it.

## Spelling

American English in code, comments, docs and generated text.

## Drawings

An isometric overview diagram with a ×6 corner-rib inset, and dimensioned
technical drawings (top plan, front elevation, magnet-bore and stacking-joint
detail sheet). A drawing change, and every release bump, refreshes the
README's copy in `docs/images/` (unversioned names), alt text included.

- No view hand-tunes `set_xlim`/`set_ylim`. Most call `ax.autoscale_view()`
  plus `ax.margins()`; the two-panel detail sheet uses `_fit_view` so both
  panels share one scale. Dimension labels are `ax.text`, which never
  reaches `dataLim`, so plain autoscaling crops them: `_fit_view` corrects
  for that, and the other views' `ax.margins()` must leave room for their
  own dimension text.

## Design constraints that must not be regressed

- Magnet bores share X positions on the front and back faces and are
  symmetric about the X centerline so plates mate either way round.
- Plate must fit the `printer=` profile (X, Y, height); with none, X <= 246 mm.
- Corner stacking ribs (top face) and grooves (bottom face) are positioned
  off `plate_x`/`plate_y` only, never off pocket or blank layout, so any two
  plates sharing this outer footprint stack together.
- Nothing here may depend on a specific blank's dimensions. A change that
  references a card, part or pocket size belongs in a blank-specific script
  layered on top of this one.
