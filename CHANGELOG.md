# Jig Plate — Changelog

| | |
|---|---|
| **Generator (CLI)** | `jig-plate.py` |
| **Generator (library)** | `jig_plate_base.py` (`build_plate()`) |
| **Meshes** | `jig_plate_<version>.stl` |
| **Latest release** | 3.0.0 |

## Versioning

`major.minor.iterative`

| Field | Rule |
|---|---|
| `major` | Bumped only on explicit command; zeroes minor and iterative |
| `minor` | Bumped only on explicit command; zeroes iterative |
| `iterative` | Incremented automatically on any change to the generated model: a change to the plate's default output (geometry, dimensions, positions) *or* a change to how the model is generated (parameters, CLI options, generation logic), even if the default output itself is unaffected. A default-output change is the clearer, more common case. |

Every change to the generated model gets an entry here, newest first,
saying what changed for the user and citing issue numbers. Iterative entries
up to 3.0.0 were recorded only in the `Changelog` block of the generator
docstring and folded into the release entries below; from 3.0.1 on, each
iterative change has its own entry here as well.

Each version's number appears in three places and they are kept in sync: the
`VERSION` constant in `jig-plate.py` (also mirrored in `pyproject.toml`),
the mesh filenames, and the 80-byte binary STL header of each mesh (readable
with `head -c 80 file.stl`). The generator's own filename (`jig-plate.py`)
never changes -- it isn't one of the three.

---

## 3.0.0 — Lightening cutout reverted; derived-geometry validation

Major release. Folds iterative changes 2.4.1–2.4.13 into a versioned
release — six rounds of independent code review plus a full reversal of
2.4.0's headline feature.

### Removed

- **Bottom-face lightening cutout, entirely.** 2.4.0's honeycomb was
  built out further (cell-size CLI flag, a sparse-coffer alternative,
  a thinner top skin — 2.4.1–2.4.4) and then fully reverted (2.4.5):
  material and print-time reduction is handled in the slicer (infill)
  instead of the model. `build_plate()` and the CLI no longer have
  `honeycomb_*`/`coffer_*` parameters or `--lightening`/`--honeycomb-*`/
  `--coffer-*` flags. The default plate is a solid slab again, matching
  2.3.0/pre-2.3.1 — this release nets out to **no change** in the
  lightening feature versus what shipped before 2.4.0, only churn in
  between.

### Added

- **Derived-geometry validation.** `build_plate()` previously took
  almost no input validation — most bad parameter combinations either
  crashed with an unrelated matplotlib/trimesh error or silently built
  a "watertight" plate with merged, overlapping, or paper-thin-walled
  features. It now checks every mechanical feature (magnet bores,
  stacking rib/groove) and the debossed branding as an axis-aligned
  bounding box, verifying each stays within the plate — with a real
  0.8mm minimum wall, not just non-overlap — on every axis it isn't
  deliberately anchored to a face on, and doesn't come within 0.8mm of
  any other feature. One mechanism now catches every reported "still
  builds a broken plate" case, independent of which parameter
  combination causes it, replacing a growing pile of bespoke
  per-parameter checks that kept missing new ones every review round.
- **Full X/Y/Z fit play in the stacking rib/groove.** `stack_play`
  already widened the groove beyond the rib's own footprint in X and Y
  (since 2.1.3/2.2.0); it now does the same for Z. The groove is cut
  `stack_h + stack_play` deep instead of exactly `stack_h`, so the rib
  no longer bottoms out with zero vertical clearance when two plates
  stack. Framed against the actual mesh: the groove measured 1.6mm deep
  before 2.4.6 (a stray overcut bug, not deliberate clearance), 1.5mm
  from 2.4.6 through 2.4.12 (the overcut fixed, leaving true zero
  clearance), and is 1.7mm now — net +0.1mm versus the pre-2.4.6/2.4.0
  mesh, and the first time this clearance has been a deliberate choice.

### Fixed

- STL header truncation could silently corrupt the file for a header
  ≥ 80 bytes (not reachable at current label/version lengths, but no
  longer a landmine); both STL headers understated the plate's height
  (9mm instead of the true 10.5mm with the stacking ribs).
- Debossed labels containing a balanced `$...$` pair were silently
  parsed as LaTeX mathtext instead of literal text; labels with
  characters the debossed font has no glyph for produced a visible
  placeholder "tofu" box instead of failing.
- The isometric diagram's projection was mirrored (wrong winding); the
  front elevation never drew the corner stacking ribs; the top-plan
  view drew front/back magnet bores at the wrong size and, separately,
  never drew the stacking grooves at all (only the ribs); the
  magnet-bore-detail and stacking-joint panels each had a missing or
  mis-hatched face edge at various points across this range.
- Packaging: `rtree` and `pytest` were only in `requirements.txt`, not
  `pyproject.toml` or the README's requirements list.
- Documentation: several stale or inconsistent statements corrected —
  `CLAUDE.md`'s release-tag format and a pre-2.0.0 filename reference,
  `README.md`'s magnet-polarity wording (now distinguishes bore
  *position* symmetry from polarity compatibility under a 180° plate
  rotation, rather than reading as a contradiction) and its test-coupon
  description (now notes it also carries the rightmost front push-fit
  bore), and this file's now-resolved note about tracking a
  since-reverted feature.

### Test suite

Grew from 0 tests at 2.4.0 to 86, added across all six review rounds
and largely built against the actual mesh (ray-casting, `contains()`)
rather than the input parameters, so a bug in the real boolean geometry
can't hide behind metadata that merely echoes its inputs. Every check
added this range was verified, by temporarily reintroducing the bug it
targets, to actually fail — not just pass regardless of the underlying
geometry.

### Why a major bump

Two things closing out together justified more than another minor
release: the lightening cutout that was 2.4.0's whole reason for
existing is now fully gone (net a no-op versus pre-2.4.0, but a
significant round trip), and `build_plate()`'s validation contract
changed fundamentally — from essentially none to a structural
derived-geometry check that every future feature is expected to plug
into. Together they mark a clean line for anyone building on this repo
between "before" and "after," which a `2.5.0` wouldn't communicate.

### Result

**481.5 cm³, bounding box 246 × 218 × 10.5 mm — unchanged from 2.3.0,
having gone by way of 2.4.0's 285.5 cm³ honeycomb and back.** Top face,
all 12 magnet bores, and the corner stacking rib/groove system are
geometrically untouched apart from the deliberate +0.1mm groove-depth
clearance described above. Stack coupon unchanged at 8.09 cm³. Verified
watertight (plate and coupon).

### Validation

Not yet printed under this name. The corner stacking joint this release
depends on (2.2.0) was already printed and physically test-stacked with
a confirmed good fit at the pre-3.0.0 depth; the deeper groove has not
itself been physically validated, though it can only make the rib seat
more easily, never obstruct it (see Added, above).

### Files

- `jig-plate.py`
- `jig_plate_base.py`
- `tests/test_jig_plate_base.py`
- `README.md`
- `CLAUDE.md`

### Generated Files

- `jig_plate_3.0.0.stl`
- `jig_plate_3.0.0_stack_coupon.stl`

---

## 2.4.0 — Bottom-face honeycomb lightening cutout

Minor release. Folds iterative changes 2.3.1–2.3.3 into a versioned
release.

### Added

- **Honeycomb lightening cutout on the bottom face.** A hex grid of blind
  pockets is cut up from the bottom face by default, leaving a thin top
  skin (`honeycomb_skin`, 2.4 mm) and a honeycomb wall between cells
  (`honeycomb_wall`, 2.6 mm). Cell size (`honeycomb_af`, default 22 mm
  across flats — also exposed as `--honeycomb-af` on the CLI) and
  orientation match eu-business-card-jig's vented pocket floor. The
  lattice is built full-coverage across the margin-inset field
  (`honeycomb_margin_x`/`honeycomb_margin_y`) and then clipped — via a
  boolean intersection against that field and a boolean difference
  against the bottom-corner mounting-magnet-bore and corner
  stacking-rib/groove footprints (with clearance) — rather than dropping
  any cell that doesn't fit whole; sub-3 mm² slivers left over from
  clipping are discarded. Opt out with `honeycomb_enabled=False` for a
  solid underside. New keyword arguments only — no existing parameter's
  default or signature changed.

### Why

The base plate was a near-solid slab (91% of its default volume being a
uniform 9 mm block), which is unnecessary material and print time for a
part that's mostly a rigid spacer between the top registration surface
and the bottom mounting/stacking features. A honeycomb wins over a plain
rectangular waffle grid on convex-cell packing efficiency, and clipping
boundary cells (instead of dropping them) recovers material a
drop-if-it-doesn't-fit grid would otherwise waste at the field edges. The
22 mm default cell size was chosen over the initial 23.1 mm match to
eu-business-card-jig as a deliberate, slightly denser trade of a little
extra wall material for a tighter, more supportive lattice.

### Result

**285.5 cm³, bounding box 246 × 218 × 10.5 mm — down from 481.5 cm³ at
2.3.0, a 40.7% reduction.** Top face, all 12 magnet bores, and the corner
stacking rib/groove system are geometrically untouched; the stack coupon
is unchanged at 8.09 cm³. Verified watertight (plate and coupon).

### Validation

Not yet printed under this name. The corner stacking joint this release
depends on (2.2.0) was already printed and physically test-stacked with
a confirmed good fit; the honeycomb floor itself has not been physically
load-tested for rigidity under clamping pressure.

### Files

- `jig-plate.py`
- `jig_plate_base.py`

### Generated Files

- `jig_plate_2.4.0.stl`
- `jig_plate_2.4.0_stack_coupon.stl`

---

## 2.3.0 — Branding duplicated on both side faces

Minor release. Folds iterative change 2.2.1 into a versioned release.

### Changed

- **Debossed logo/label duplicated on the right face** (`x=plate_x`),
  matching the existing left-face deboss. Each side face is mirrored to
  read correctly from its own outward-facing direction — the right face
  is not a plain copy of the left-face cut, since a viewer reading the
  left face has "right" = −Y while a viewer reading the right face has
  "right" = +Y, the opposite sign. Verified by rendering each face's cut
  as its own viewer would see it: both read "Jig Plate" correctly, not
  mirrored or backwards.

### Result

481.5 cm³, bounding box 246 × 218 × 10.5 mm — unchanged from 2.2.0 at
display precision.

### Validation

Not yet printed under this name. The corner stacking joint this release
depends on (2.2.0) was already printed and physically test-stacked with
a confirmed good fit.

### Files

- `jig-plate.py`
- `jig_plate_base.py`

### Generated Files

- `jig_plate_2.3.0.stl`
- `jig_plate_2.3.0_stack_coupon.stl`

---

## 2.2.0 — Corner stacking joint tightened and validated

Minor release. Folds iterative changes 2.1.1–2.1.3 into a versioned
release.

### Changed

- **Corner stacking rib/groove reinset**: `stack_inset_x` 6 → 4 mm, and a
  new `stack_inset_y` (4 mm) decouples the rib/groove's Y position from
  the mounting-magnet border bands it previously borrowed — now a fixed
  4 mm inset from each corner on both axes.
- **Bottom-corner mounting magnets brought in**: `bottom_mag_inset_x`
  20 → 12 mm, toward the stacking rib/groove (the nearer feature — their
  Y-bands already overlapped; only X separated them). Gives a 1.85 mm
  wall between magnet bore and stacking rib/groove.
- **Stacking groove gained fit play lengthwise**: `stack_play` now widens
  the groove on both axes (previously width-only). Groove is
  6.2 × 1.7 mm against a 6.0 × 1.5 mm rib.

### Result

481.5 cm³, bounding box 246 × 218 × 10.5 mm — unchanged from 2.1.0 at
display precision. Tightest perimeter wall on the plate is now 0.9 mm
(stacking-groove edge clearance), down from 3 mm at 2.1.0.

### Validation

**Corner stacking coupon printed and physically test-stacked: fit
confirmed good.** First physical validation of the stacking joint since
the corner-tightening changes in this release.

### Files

- `jig-plate.py`
- `jig_plate_base.py`

### Generated Files

- `jig_plate_2.2.0.stl`
- `jig_plate_2.2.0_stack_coupon.stl`

---

## 2.1.0 — Symmetric front/back border margins

Minor release. Folds iterative change 2.0.1 into a versioned release.

### Changed

- **Default `back_margin` reduced from 17 mm to 10 mm**, matching
  `front_margin`. The back-corner mounting magnet bore and stacking
  rib/groove — previously 5.45 mm from the back edge while the
  equivalent front-side features sat only 1.95 mm from the front edge —
  now share the same 1.95 mm edge clearance on both sides.

### Why

The asymmetry had no design reason behind it: the front margin's 1.95 mm
bore-to-edge clearance is already the validated value this design relies
on, so matching the back margin to it removes an arbitrary difference
rather than introducing a new, unvalidated one.

### Result

Unchanged from 2.0.0: 481.5 cm³, bounding box 246 × 218 × 10.5 mm.
Verified no collision — the back-corner mounting magnet bore and stacking
rib/groove stay separated in X (7.95 mm gap) regardless of sharing a Y
position — and the plate is still watertight.

### Validation

Not yet printed under this name.

### Files

- `jig-plate.py`
- `jig_plate_base.py`

### Generated Files

- `jig_plate_2.1.0.stl`
- `jig_plate_2.1.0_stack_coupon.stl`

---

## 2.0.0 — Importable library, two-file architecture

Major release. Folds iterative change 1.1.1 in. Breaking change to the
project's structure (not to the plate itself): the generator is no longer
one script.

### Changed

- **Split into two files.** `jig_plate_base.py` is a new, properly
  importable library module (a hyphenated filename like `jig-plate.py`
  can't itself be `import`ed) holding all plate geometry: `build_plate()`,
  and the `PlateGeometry`/`PlateResult` dataclasses. `jig-plate.py` is now
  a thin CLI wrapper around it — argument parsing, STL export, and the
  diagrams/technical drawings only.
- **Public API for other generator scripts.** A blank-specific pocket-layout
  script now builds on this base plate by importing directly —
  `from jig_plate_base import build_plate` — with no CLI, no file I/O, and
  no argument parsing involved. `build_plate()` accepts every plate
  dimension, margin, magnet spec, stacking-joint dimension, and the
  debossed label as keyword arguments, and returns a `PlateResult` whose
  `.geometry` exposes every magnet-bore and stacking-rib/groove position so
  pockets can be laid out around them.

### Why a major bump

This changes what "the generator" means for this project: from one script
to a documented two-file split with `jig_plate_base.build_plate()` as the
supported integration point for other scripts. Nothing about the physical
plate changes.

### Result

Unchanged from 1.1.0: 481.5 cm³, bounding box 246 × 218 × 10.5 mm. Verified
`build_plate()` called with no arguments reproduces the exact default plate
(identical volume, bounding box, face count) both directly and through the
refactored CLI; `--label`, the stack coupon, and all three
diagrams/technical drawings verified unchanged.

### Validation

Not yet printed under this name.

### Files

- `jig-plate.py`
- `jig_plate_base.py`

### Generated Files

- `jig_plate_2.0.0.stl`
- `jig_plate_2.0.0_stack_coupon.stl`

---

## 1.1.0 — Configurable label, cross-platform font

Minor release. Folds iterative changes 1.0.1–1.0.2 into a versioned release.

### Added

- **`--label` CLI flag** for the debossed text on the top and left faces,
  default unchanged (`"Jig Plate"`). The logo mark next to it is not
  parameterized.

### Changed

- **Debossed label font** pinned to `"DejaVu Sans"` (the font matplotlib
  bundles internally) instead of the generic `"sans-serif"` family alias,
  so the debossed text's exact letterforms no longer depend on which
  fonts happen to be installed on the host — identical on macOS, Windows,
  and Linux.
- **Versioning policy** (`CLAUDE.md`, this file) broadened: iterative
  bumps now also cover changes to how the model is generated (parameters,
  CLI options, generation logic), not just changes to the default-output
  geometry. Both changes above shipped under this broadened rule even
  though the default output was unaffected.

### Result

Unchanged from 1.0.0: 481.5 cm³, bounding box 246 × 218 × 10.5 mm. Verified
identical (volume, bounding box, face count) with the default label on this
machine; a custom `--label` value was verified to still produce a
watertight mesh.

### Validation

Not yet printed under this name.

### Files

- `jig-plate.py`

### Generated Files

- `jig_plate_1.1.0.stl`
- `jig_plate_1.1.0_stack_coupon.stl`

---

## 1.0.0 — First stable release

Major release. Script and documentation reviewed end to end; no geometry
changes.

### Changed

- Removed dead code (`det_z0`/`det_z1`, computed but never used) from the
  stacking-joint detail drawing in `_tech_detail`. Documentation only — the
  technical drawings are unaffected.
- Corrected two documentation inconsistencies found during review:
  - The plate's corner-stacking-rib height was mislabeled 10 mm in
    `README.md` and the 0.1.0 changelog entry below; the correct figure
    (`PLATE_Z + STACK_H` = 9 + 1.5) is 10.5 mm.
  - The 0.1.0 changelog entry's "Files" section named a version-suffixed
    script filename (`jig-plate_0.1.0.py`) that doesn't match the actual,
    unversioned script filename (`jig-plate.py`).

### Result

Unchanged from 0.1.0: 481.5 cm³, bounding box 246 × 218 × 10.5 mm. Verified
identical (volume, bounding box, face count) before and after the dead-code
cleanup.

### Validation

Not yet printed under this name.

### Files

- `jig-plate.py`

### Generated Files

- `jig_plate_1.0.0.stl`
- `jig_plate_1.0.0_stack_coupon.stl`

---

## 0.1.0 — Baseline

First versioned release. Establishes the base plate: no blank-specific
pockets of any kind, only the geometry every pocket layout can be built on
top of without modification.

### Plate

- Footprint: 246 × 218 × 9 mm (10.5 mm at the corner stacking ribs)
- No pocket cavities, lips, vented floor, finger divots, or pocket-level
  registration marks — this is deliberately a blank plate

### Magnets

- 8 push-fit magnet bores (Ø6.1 × 3.2 mm deep) in the front and back faces,
  symmetric about the X centreline so plates mate either way round
- 4 more push-fit magnet bores in the bottom-face corners, for mounting the
  plate itself (e.g. to a magnetic base)

### Corner stacking ribs and grooves

Top-face rib at each of the four corners seats into the matching bottom-face
groove of the plate above, positioned off the plate's outer footprint rather
than any pocket layout, so plates holding different blanks still stack
together. This is the only registration feature on this base plate.

### Branding

Debossed "Jig Plate" wordmark and logo mark on the top face's front frame
edge, duplicated on the left face for readability when plates are stacked
or stored on edge.

### Test coupon

A corner piece carrying the stacking rib/groove and its mounting magnet, for
validating the stacking fit independently of whatever pocket layout gets
added later.

### Result

Base plate only, no pocket cavities: 481.5 cm³, bounding box
246 × 218 × 10.5 mm (the extra 1.5 mm at the corner stacking ribs).

### Validation

Not yet printed under this name.

### Files

- `jig-plate.py`

### Generated Files

- `jig_plate_0.1.0.stl`
- `jig_plate_0.1.0_stack_coupon.stl`
