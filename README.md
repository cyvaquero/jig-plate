# Jig Plate

A parametric 3D-printable **base plate** for laser-engraving jigs. It carries
the magnet system and stacking joint shared by every jig built on it, with no
pocket geometry of its own — pockets for a specific blank (business cards,
tags, coasters, whatever) get added to this base in a separate script.

`jig-plate.py` generates the base plate and a corner test coupon as
watertight binary STL, plus a labelled diagram and dimensioned technical
drawings. The actual plate geometry lives in the importable
`jig_plate_base.py` library, so another generator script can build on this
base plate without running the CLI — see [Using it as a library](#using-it-as-a-library)
below.

## Features

- **Corner stacking ribs and grooves** — blank-agnostic vertical registration
  between plates: a top-face rib at each of the four corners seats into the
  matching bottom-face groove of the plate above, positioned off the plate's
  outer footprint rather than any pocket layout, so plates holding different
  blanks still stack together
- **8 magnet bores** (Ø6.1 mm, push-fit for 6 × 3 mm magnets) in the front and
  back faces, symmetric about the centreline so a plate's bore *positions*
  still line up with its neighbours' if it's turned 180° -- see the polarity
  note under [Printing notes](#printing-notes): the fixed front/back polarity
  convention below matches unrotated plates to each other, not a plate
  rotated 180° to its unrotated neighbours
- **4 more magnet bores** (same Ø6.1 mm / 6 × 3 mm spec) in the bottom-face
  corners, for mounting the plate itself
- **Debossed branding** — logo mark plus a text label (default "Jig Plate",
  override with `--label`) recessed into the top face's front frame edge,
  duplicated on the left and right faces (each mirrored to read correctly
  from its own side) for readability when plates are stacked or stored on
  edge
- **Test coupon** — a corner piece carrying the stacking rib/groove, its
  bottom mounting magnet, and (at the default `mag_xs`) the rightmost front
  push-fit bore, which also falls inside this corner's cut region -- for
  validating the stacking fit *and* the wall between the mounting bore and
  the stacking rib/groove (1.85 mm at the defaults), independently of any
  pocket layout added later

## Dimensions

| | |
|---|---|
| **Plate** | 246 × 218 × 9 mm (10.5 mm at the corner stacking ribs) |

## Requirements

- Python 3.11+
- [trimesh](https://trimesh.org/) with the
  [Manifold](https://github.com/elalish/manifold) boolean engine
- NumPy, Shapely, Matplotlib
- pytest, rtree (for the test suite -- see [Tests](#tests))

```bash
python3.14 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements.lock
```

`requirements.lock` pins every dependency, direct and transitive, to an exact
version with hashes, so a fresh venv reproduces the same meshes. It targets
Python 3.14 (`manifold3d` has no wheel for 3.15 yet). `requirements.txt` is
the loose, unpinned input. To regenerate the lock after changing it, from a
Python 3.14 venv with [pip-tools](https://pip-tools.readthedocs.io/)
installed (`pip install pip-tools`):

```bash
pip-compile --generate-hashes --output-file requirements.lock requirements.txt
```

## Usage

```bash
.venv/bin/python jig-plate.py
```

Optionally override the debossed text label (the logo mark is always
included and is not parameterized):

```bash
.venv/bin/python jig-plate.py --label "Card Jig"
```

Generates into `output/`:

- `jig_plate_<version>.stl` — the base plate
- `jig_plate_<version>_stack_coupon.stl` — corner test piece carrying the
  stacking rib/groove and its mounting magnet

And into `images/`:

- `jig_plate_<version>_diagram.png` — isometric plate overview
- `jig_plate_<version>_tech_top.png` — dimensioned top plan view
- `jig_plate_<version>_tech_front.png` — front elevation
- `jig_plate_<version>_tech_detail.png` — magnet-bore and stacking-joint
  detail sheet

The script prints watertight status, volume, bounding box, and face count for
both meshes. Both must report `watertight: True` or the geometry is broken.

## Tests

Unit tests cover `jig_plate_base.build_plate()` directly (watertightness,
volume, bounding box, and the design constraints in `CLAUDE.md`) -- fast
enough to run after every change, no need to run the full CLI/diagram
pipeline just to check the geometry is still sound:

```bash
.venv/bin/pytest
```

## Using it as a library

A hyphenated filename can't be `import`ed, so the reusable geometry lives
in `jig_plate_base.py` instead. A blank-specific generator script builds
pockets on top of this base by importing `build_plate` directly, with no
CLI, no file I/O, and no argument parsing involved:

```python
from jig_plate_base import build_plate

result = build_plate()                      # defaults match the CLI exactly
result = build_plate(label="Card Jig")       # or override any parameter

result.solid              # trimesh.Trimesh — the base plate, no pockets
result.geometry.mag_xs    # front/back magnet-bore X positions
result.geometry.stack_xs  # corner stacking rib/groove X positions
result.geometry.stack_ys  # ...and Y positions — avoid these zones when
                           # laying out pockets on top of the returned solid
```

`build_plate()` accepts every plate dimension and margin as a keyword
argument (plate size, magnet spec/count/spacing, stacking rib/groove
dimensions, the debossed label). See `jig_plate_base.py` for the full
parameter list — all of it defaults to the same base plate this CLI ships.

## Printing notes

- Print flat, top face up.
- Press 6 × 3 mm magnets into the bores. Keep polarity consistent: one pole out
  on every front-face magnet, the opposite on every back-face magnet, or some
  pairs will repel. This convention attracts an *unrotated* neighbour (the
  common case, plates arranged front-to-back in a row); a plate turned 180°
  presents what was its back face where a front face is expected, so its
  magnets would need the opposite polarity from this rule to still attract
  rather than repel there.

## Versioning

`major.minor.iterative` — `VERSION` in the script is the single source of truth
and drives output filenames and the 80-byte binary STL header. See
[CHANGELOG.md](CHANGELOG.md) for release history.

## License

No license file is included. All rights reserved unless otherwise stated.
