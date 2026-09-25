# Jig Plate — Changelog

| | |
|---|---|
| **Generator** | `jig-plate.py` |
| **Meshes** | `jig_plate_<version>.stl` |
| **Latest release** | 1.0.0 |

## Versioning

`major.minor.iterative`

| Field | Rule |
|---|---|
| `major` | Bumped only on explicit command; zeroes minor and iterative |
| `minor` | Bumped only on explicit command; zeroes iterative |
| `iterative` | Incremented automatically on every change to the model geometry or to how the model is generated (parameters, CLI options, generation logic), even if the default output is unaffected |

**This file records major and minor releases only,** newest first. Iterative
changes are not given entries here; they are folded into the next minor release
when one is cut. The running record of every iterative change is the `Changelog`
block in the generator docstring, which is updated on every model change.

Each version's number appears in three places and they are kept in sync: the
generator filename, the mesh filenames, and the 80-byte binary STL header of
each mesh (readable with `head -c 80 file.stl`).

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
