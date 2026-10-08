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
prints `watertight: True` for the plate and `stack coupon: True` for the
coupon (that flag is its watertightness) — if either is `False`, the
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

- **iterative**: bump automatically, once per change (not per commit), for
  every change merged to `develop`: geometry, generation logic, CLI,
  drawings, tests, docs, `CLAUDE.md`. Follow-up fixes to an unmerged PR keep
  that PR's version and amend its entries rather than bumping again.
- **minor / major**: bump only when explicitly told to; zero the fields below it.
- Pre-release suffixes (`-rc`, `-beta`) only on request.

Every change gets a `CHANGELOG.md` entry, newest first, saying what changed
for the user and citing the issue numbers it addresses. Also keep the
`Changelog` block of the script docstring in step: a short summary line plus
as many follow-up lines as needed to name what changed, why, and what was
verified.

## CHANGELOG consolidation at release

When a release bumps the major or minor version, squash the iterative entries
it covers into that version's section. The individual `x.y.N` headings are
removed from the file; git history keeps them.

Scope:
- The squash covers every iterative entry from the previous major or minor
  heading down to (not including) this one.
- A bump with no feature content of its own still consolidates the range below
  it. "Same features as <previous>" is not a reason to skip it.
- Never touch a section at or below an already-consolidated heading.

Backfill:
- Before consolidating the current release, walk the file for earlier major or
  minor headings whose range still has loose `x.y.N` entries under it. Squash
  each, same rules, oldest first.
- A heading is already consolidated when no `x.y.N` headings remain between it
  and the next major or minor heading below. Don't re-process those.
- Report what you backfilled, separately from the current release.

How to squash:
- Group under Keep a Changelog headings in this order: Added, Changed,
  Deprecated, Removed, Fixed, Security. Omit empty groups.
- One bullet per user-visible outcome, not per iterative entry or per PR.
  Several entries that moved one feature forward collapse into the single
  sentence describing where it landed.
- Carry every issue number forward. A merged bullet cites all of them:
  `(#12, #19, #23)`. Losing a reference is a defect.
- Write the end state, not the journey. An add-then-fix pair inside the range
  becomes the end state alone, since no user saw the intermediate.
- Every security entry in the range gets a bullet. Security is not subject to
  the merging and dropping rules above — under-reporting hardening in a public
  repo is a defect.
- Drop entries with no user-facing effect (test fixtures with no app change,
  internal reorganization, docs-only corrections) unless they changed behavior,
  defaults, or output.
- Preserve the exact wording of any entry that already reads as a release-level
  statement rather than rewriting it for style.
- Keep measured figures (timings, percentages, dimensions) where the entry gave
  them; they're the evidence the change was verified.

Constraints:
- Do not renumber, re-date, or reorder released sections.
- Do not invent entries. If a referenced issue number has no matching iterative
  entry, stop and ask rather than reconstructing from the diff.
- Report per range: range covered, entries in, bullets out, and anything
  dropped with the reason.

## Verified output formats

These must stay byte-for-byte identical unless a change is meant to alter
them. Before and after any change, run the CLI and compare: report the
regression result.

- `output/jig_plate_<VERSION>.stl` and `output/jig_plate_<VERSION>_stack_coupon.stl`:
  binary STL whose 80-byte header starts `Jig plate <VERSION>` and is
  NUL-padded. Both meshes must report watertight (`watertight: True`,
  `stack coupon: True`). Across a version
  bump, only the filename and header bytes may differ; compare the
  triangle data (bytes 80 onward) with `cmp`.
- `images/*.png`: the isometric diagram and three technical-drawing sheets.
  Compare these visually; matplotlib PNGs aren't byte-stable across
  library versions.
- `build_plate()` return shape: `PlateResult(solid, geometry)` and the
  `PlateGeometry` fields that blank-specific generators import.

## Git

Strict git-flow; the account-level rules (branch naming, PRs, approvals,
issue filing, release procedure) apply in full. Repo-specific points:

- `feature/` and `bugfix/` branch off `develop` and reach it by PR; never
  commit directly to `develop` or `main`.
- Releases: `release/x.y.z` off `develop`, merged to `main` and tagged
  `vx.y.z`, then merged back to `develop` — only on explicit approval.
  There is no `RELEASING.md`; the account release procedure applies as
  written.
- The default branch is `main`, so PRs into `develop` or a release branch
  don't auto-close issues. Close those by hand with
  "Fixed in #PR (vX.Y.Z)".
- Commit identity: `Guy Heckman <1611555+cyvaquero@users.noreply.github.com>`.
  The sandbox can't read `~/.gitconfig`, so run git with
  `GIT_CONFIG_GLOBAL` pointing at a file that holds only the gh
  credential helper, and pass the identity through the
  `GIT_AUTHOR_*`/`GIT_COMMITTER_*` env vars.
- Only `severity:low` exists among the review labels so far; create the
  other `severity:*` labels, `code-review` and `deferred` (color
  `BFD4F2`) the first time an issue needs one.

## Blind review scope

There is no UI. The accessibility reviewer is limited to the docs
(README images need text alternatives), the CLI output, and the
generated drawings (legibility, use of color, contrast of the labels).

## Spelling

American English in code, comments, docs and generated text.

## Drawings

Alongside the mesh the script renders an isometric overview diagram and
dimensioned technical drawings (top plan, front elevation, and a detail sheet
carrying the magnet-bore and stacking-joint cross-sections). These are
documentation, not geometry, but a drawing change still bumps the iterative
version and gets a changelog entry like any other change.

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
  about the X centerline so plates mate either way round.
- Plate must stay <= 246 mm in X (bed width plus purge-area clearance).
- Corner stacking ribs (top face) and grooves (bottom face) are positioned
  off `plate_x`/`plate_y` only, never off pocket or blank layout, so any two
  plates sharing this outer footprint stack together regardless of what
  pockets get added to each later.
- Nothing in this script may depend on a specific blank's dimensions. If a
  change references a card, part, or pocket size, it belongs in a
  blank-specific script layered on top of this one, not here.
