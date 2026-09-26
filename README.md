# Jig Plate

A parametric 3D-printable **base plate** for laser-engraving jigs. It carries
the magnet system and stacking joint shared by every jig built on it, with no
pocket geometry of its own — pockets for a specific blank (business cards,
tags, coasters, whatever) get added to this base in a separate script.

One Python script, `jig-plate.py`, generates the base plate and a corner test
coupon as watertight binary STL, plus a labelled diagram and dimensioned
technical drawings.

## Features

- **Corner stacking ribs and grooves** — blank-agnostic vertical registration
  between plates: a top-face rib at each of the four corners seats into the
  matching bottom-face groove of the plate above, positioned off the plate's
  outer footprint rather than any pocket layout, so plates holding different
  blanks still stack together
- **8 magnet bores** (Ø6.1 mm, push-fit for 6 × 3 mm magnets) in the front and
  back faces, symmetric about the centreline so plates mate either way round
- **4 more magnet bores** (same Ø6.1 mm / 6 × 3 mm spec) in the bottom-face
  corners, for mounting the plate itself
- **Debossed branding** — logo mark plus a text label (default "Jig Plate",
  override with `--label`) recessed into the top face's front frame edge,
  duplicated on the left face for readability when plates are stacked or
  stored on edge
- **Test coupon** — a corner piece carrying the stacking rib/groove and its
  mounting magnet, for validating the stacking fit independently of any
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

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
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

## Printing notes

- Print flat, top face up.
- Press 6 × 3 mm magnets into the bores. Keep polarity consistent: one pole out
  on every front-face magnet, the opposite on every back-face magnet, or some
  pairs will repel.

## Versioning

`major.minor.iterative` — `VERSION` in the script is the single source of truth
and drives output filenames and the 80-byte binary STL header. See
[CHANGELOG.md](CHANGELOG.md) for release history.

## License

No license file is included. All rights reserved unless otherwise stated.
