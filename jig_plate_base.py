"""Importable base-plate geometry library for the stackable laser jig.

`jig-plate.py` cannot itself be `import`ed (a hyphen isn't a valid Python
identifier), so the actual reusable geometry lives here instead: any
blank-specific generator script can

    from jig_plate_base import build_plate
    result = build_plate()          # or build_plate(label="Card Jig")
    result.solid                    # trimesh.Trimesh, the base plate
    result.geometry.mag_xs          # reserved zones to build pockets around
    result.geometry.stack_xs        # ...

`build_plate` has no side effects -- it does not touch argv, stdout, or the
filesystem, and returns the solid plus every derived position (magnet
bores, corner stacking rib/groove zones) so a pocket-layout script can lay
out pockets that avoid them. File I/O, diagrams, and the CLI stay in
`jig-plate.py`.
"""
import dataclasses

import numpy as np
import trimesh
from trimesh.creation import box, extrude_polygon
from shapely.geometry import Polygon, MultiPolygon


@dataclasses.dataclass(frozen=True)
class PlateGeometry:
    """Every position a pocket-layout script needs to build on top of the
    plate without colliding with its magnet bores or stacking rib/groove."""

    plate_x: float
    plate_y: float
    plate_z: float
    front_margin: float
    back_margin: float
    mag_d: float
    mag_depth: float
    mag_xs: tuple
    bottom_mag_inset_x: float
    bottom_mag_ys: tuple
    stack_w: float
    stack_len: float
    stack_h: float
    stack_play: float
    stack_inset_x: float
    stack_inset_y: float
    stack_xs: tuple
    stack_ys: tuple
    label: str
    deboss_d: float


@dataclasses.dataclass(frozen=True)
class PlateResult:
    solid: "trimesh.Trimesh"
    geometry: PlateGeometry


def bx(x0, y0, z0, x1, y1, z1):
    """Axis-aligned box between two corners. Reused by pocket-layout
    scripts building cuts on top of the plate."""
    m = box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


def _logo_polys(cx, cy):
    """Logo: semicircle dome (+Y) with three rows of tapered bar pairs."""
    r = 2.5
    angles = np.linspace(0, np.pi, 64)
    semi = [(cx + r * np.cos(a), cy + r * np.sin(a)) for a in angles]
    parts = [Polygon(semi)]
    gap, bh, sp = 0.4, 0.65, 0.4
    y0 = cy - 0.5
    for i, w in enumerate([3.0, 2.5, 2.0]):
        yt = y0 - i * (bh + sp)
        yb = yt - bh
        parts.append(Polygon([(cx-w, yt), (cx-gap, yt), (cx-gap, yb), (cx-w, yb)]))
        parts.append(Polygon([(cx+gap, yt), (cx+w, yt), (cx+w, yb), (cx+gap, yb)]))
    return parts


def _label_font_properties():
    from matplotlib.font_manager import FontProperties as _FP
    # pinned to the font matplotlib bundles internally (not a system font),
    # so the debossed text is identical on macOS, Windows, and Linux
    return _FP(family="DejaVu Sans", weight="bold")


def _unsupported_label_chars(text):
    """Characters in `text` with no real glyph in the debossed font
    (DejaVu Sans) -- e.g. CJK or other scripts it doesn't cover, or
    control characters like a literal newline. Rendering these anyway
    doesn't fail: the font's .notdef glyph is a visible placeholder box
    that would get debossed as-is, so the caller should reject them with
    a clear message instead."""
    import matplotlib.ft2font as _ft2font
    from matplotlib.font_manager import findfont as _findfont
    font = _ft2font.FT2Font(_findfont(_label_font_properties()))
    seen = {}
    for ch in text:
        if ch not in seen:
            seen[ch] = font.get_char_index(ord(ch)) == 0
    return [ch for ch in dict.fromkeys(text) if seen[ch]]


def _text_polys(text, size, x0, y0):
    """Shapely polygons for extrudable text at (x0, y0) baseline."""
    from matplotlib.textpath import text_to_path as _t2p
    from matplotlib.path import Path as _Path
    from matplotlib.transforms import Affine2D as _Affine2D
    # ismath=False always: TextPath's default auto-detects mathtext from
    # a balanced pair of $ in the string, which turned "Save $5 and $6"
    # into LaTeX-formatted "Save 5and6" and made a lone "$\foo$" crash as
    # invalid mathtext syntax. This label is debossed plate branding, not
    # a formula, so every character (including $ and \) always renders
    # as its own literal DejaVu Sans glyph.
    verts, codes = _t2p.get_text_path(
        _label_font_properties(), text, ismath=False
    )
    if len(verts) == 0:
        return []
    tr = _Affine2D().scale(size / _t2p.FONT_SCALE).translate(x0, y0)
    tp = _Path(tr.transform(verts), codes)
    raw = tp.to_polygons()
    polys = []
    for v in raw:
        p = Polygon(v)
        if not p.is_valid:
            p = p.buffer(0)
        if not p.is_empty and abs(p.area) > 0.01:
            polys.append(p)
    polys.sort(key=lambda p: abs(p.area), reverse=True)
    out = []
    for p in polys:
        hit = False
        for i, o in enumerate(out):
            if o.contains(p.representative_point()):
                out[i] = o.difference(p)
                hit = True
                break
        if not hit:
            out.append(p)
    return out


def _add_deboss(poly_list, target, plate_z, deboss_d):
    """Extrude polys as cut volumes and append to target list."""
    for p in poly_list:
        geoms = list(p.geoms) if isinstance(p, MultiPolygon) else [p]
        for g in geoms:
            if g.is_empty or abs(g.area) < 0.01:
                continue
            m = extrude_polygon(g, height=deboss_d + 0.2)
            m.apply_translation((0, 0, plate_z - deboss_d))
            target.append(m)


def _add_deboss_left(poly_list, target, plate_y, deboss_d):
    """Deboss on the left face (x=0), readable from outside (-X)."""
    for p in poly_list:
        geoms = list(p.geoms) if isinstance(p, MultiPolygon) else [p]
        for g in geoms:
            if g.is_empty or abs(g.area) < 0.01:
                continue
            m = extrude_polygon(g, height=deboss_d + 0.2)
            verts = m.vertices.copy()
            new_v = np.empty_like(verts)
            new_v[:, 0] = verts[:, 2] - 0.2
            new_v[:, 1] = plate_y - verts[:, 0]
            new_v[:, 2] = verts[:, 1]
            m.vertices = new_v
            m.invert()
            target.append(m)


def _add_deboss_right(poly_list, target, plate_x, plate_y, deboss_d):
    """Deboss on the right face (x=plate_x), readable from outside (+X).

    Not simply _add_deboss_left with the depth flipped: a viewer at -X
    facing +X (the left face's reader) has "right" = -Y, which is why
    _add_deboss_left negates old_x into Y (plate_y - old_x) to keep
    reading order correct. A viewer at +X facing -X (this face's reader)
    has "right" = +Y instead -- the opposite sign -- so this maps old_x
    into Y directly, unflipped. (Verified via forward x up for each
    viewing direction, up = +Z.) That sign difference is exactly what
    makes this a mirror rather than a plain duplicate: same content, same
    position, opposite left/right order, each legible from its own side.
    Depth still embeds inward from x=plate_x instead of x=0, and this
    remains an orientation-reversing mapping (needs m.invert()), same as
    the left face.
    """
    for p in poly_list:
        geoms = list(p.geoms) if isinstance(p, MultiPolygon) else [p]
        for g in geoms:
            if g.is_empty or abs(g.area) < 0.01:
                continue
            m = extrude_polygon(g, height=deboss_d + 0.2)
            verts = m.vertices.copy()
            new_v = np.empty_like(verts)
            new_v[:, 0] = plate_x - (verts[:, 2] - 0.2)
            new_v[:, 1] = verts[:, 0]
            new_v[:, 2] = verts[:, 1]
            m.vertices = new_v
            m.invert()
            target.append(m)


def build_plate(
    *,
    plate_x=246.0, plate_y=218.0, plate_z=9.0,
    front_margin=10.0, back_margin=10.0,
    mag_d=6.1, mag_depth=3.2, mag_count_x=4, mag_inset_x=30.75,
    bottom_mag_inset_x=12.0,
    stack_w=1.5, stack_len=6.0, stack_h=1.5, stack_play=0.2,
    stack_inset_x=4.0, stack_inset_y=4.0,
    label="Jig Plate", deboss_d=0.3,
):
    """Build the jig plate base solid.

    No pockets -- magnet bores (front/back + bottom-corner mounting) and
    the corner stacking rib/groove system only, plus the debossed logo and
    text label. This is the base every blank-specific pocket layout builds
    on top of; see `PlateGeometry` on the result for where those reserved
    zones are so pockets can avoid them.

    `build_plate()` with no arguments reproduces the current default plate
    exactly -- see CHANGELOG.md for what the defaults are and why.

    Returns a `PlateResult` (`.solid`: trimesh.Trimesh, `.geometry`:
    PlateGeometry). Pure -- no file I/O, no argv, no printing.
    """
    # ---- input validation -----------------------------------------
    # Every check below has a reproduced failure mode behind it (a crash
    # with an unrelated/confusing error, or a silently broken/nonsensical
    # plate that still reports watertight: True) -- see CHANGELOG.md.
    if not isinstance(label, str):
        raise ValueError(f"label must be a str, got {type(label).__name__}")
    if not label.strip():
        raise ValueError("label must not be empty or whitespace-only")
    _bad_chars = _unsupported_label_chars(label)
    if _bad_chars:
        raise ValueError(
            f"label {label!r} contains characters with no glyph in the "
            f"debossed font (DejaVu Sans), which would deboss as visible "
            f"placeholder boxes instead: {_bad_chars!r}"
        )

    for _name, _value in (
        ("plate_x", plate_x), ("plate_y", plate_y), ("plate_z", plate_z),
        ("mag_d", mag_d), ("mag_depth", mag_depth),
        ("mag_inset_x", mag_inset_x),
        ("bottom_mag_inset_x", bottom_mag_inset_x),
        ("front_margin", front_margin), ("back_margin", back_margin),
        ("stack_w", stack_w), ("stack_len", stack_len),
        ("stack_h", stack_h), ("stack_play", stack_play),
        ("stack_inset_x", stack_inset_x), ("stack_inset_y", stack_inset_y),
        ("deboss_d", deboss_d),
    ):
        if isinstance(_value, bool) or not isinstance(_value, (int, float)):
            raise ValueError(
                f"{_name} must be a number, got {_value!r}"
            )
        if not np.isfinite(_value):
            raise ValueError(f"{_name} must be finite, got {_value!r}")
    if plate_x <= 0 or plate_y <= 0 or plate_z <= 0:
        raise ValueError(
            f"plate_x/plate_y/plate_z must be positive, got "
            f"({plate_x}, {plate_y}, {plate_z})"
        )
    if isinstance(mag_count_x, bool) or not isinstance(mag_count_x, int):
        raise ValueError(
            f"mag_count_x must be an int, got {mag_count_x!r}"
        )

    if plate_x > 246.0:
        raise ValueError(
            f"plate_x ({plate_x}) exceeds 246 mm (bed width + purge-area "
            "clearance -- see CLAUDE.md)"
        )
    if mag_count_x < 2:
        raise ValueError(
            f"mag_count_x ({mag_count_x}) must be >= 2 -- the bore-spacing "
            "formula divides by (mag_count_x - 1)"
        )
    if mag_depth >= plate_z:
        raise ValueError(
            f"mag_depth ({mag_depth}) must be less than plate_z ({plate_z}), "
            "or the bottom-corner mounting bore breaks through the top face"
        )
    if mag_depth >= plate_y / 2:
        raise ValueError(
            f"mag_depth ({mag_depth}) must be less than plate_y/2 "
            f"({plate_y / 2}), or the front and back push-fit bores meet "
            "or break through the opposite face"
        )
    if mag_d >= plate_z:
        raise ValueError(
            f"mag_d ({mag_d}) must be less than plate_z ({plate_z}), or "
            "the front/back push-fit bores break through the top or "
            "bottom face"
        )
    if plate_x <= 2 * mag_inset_x:
        raise ValueError(
            f"plate_x ({plate_x}) must be greater than 2 * mag_inset_x "
            f"({2 * mag_inset_x}), or the magnet-bore X positions go out "
            "of increasing order"
        )
    if stack_h >= plate_z:
        raise ValueError(
            f"stack_h ({stack_h}) must be less than plate_z ({plate_z}), "
            "or the stacking groove cuts all the way through the plate"
        )
    if stack_inset_x < stack_len / 2:
        raise ValueError(
            f"stack_inset_x ({stack_inset_x}) must be >= stack_len/2 "
            f"({stack_len / 2}), or the corner stacking rib/groove "
            "extends past the plate's left/right edge"
        )
    if stack_inset_y < stack_w / 2:
        raise ValueError(
            f"stack_inset_y ({stack_inset_y}) must be >= stack_w/2 "
            f"({stack_w / 2}), or the corner stacking rib/groove extends "
            "past the plate's front/back edge"
        )

    mag_xs = tuple(
        mag_inset_x + i * (plate_x - 2 * mag_inset_x) / (mag_count_x - 1)
        for i in range(mag_count_x)
    )
    if mag_xs[0] - mag_d / 2 < 0 or mag_xs[-1] + mag_d / 2 > plate_x:
        raise ValueError(
            "front/back magnet bores extend past the plate's left/right "
            f"edge at mag_xs={mag_xs}, mag_d={mag_d}, plate_x={plate_x}"
        )
    if mag_count_x > 1:
        _min_spacing = min(b - a for a, b in zip(mag_xs, mag_xs[1:]))
        if _min_spacing < mag_d:
            raise ValueError(
                f"front/back magnet bores overlap: spacing "
                f"({_min_spacing:.2f}) is less than the bore diameter "
                f"mag_d ({mag_d}) -- reduce mag_count_x or increase "
                "plate_x/mag_inset_x"
            )

    bottom_mag_ys = (front_margin / 2, plate_y - back_margin / 2)
    stack_xs = (stack_inset_x, plate_x - stack_inset_x)
    stack_ys = (stack_inset_y, plate_y - stack_inset_y)

    cuts, marks, scribes = [], [], []

    # push-fit magnet bores in the front (-Y) and back (+Y) faces, same X
    # positions on both so stacked plates mate face to face
    for mx in mag_xs:
        for y_face, sign in ((0.0, 1.0), (plate_y, -1.0)):
            c = trimesh.creation.cylinder(
                radius=mag_d / 2, height=mag_depth + 2, sections=64
            )
            c.apply_transform(
                trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
            )
            c.apply_translation(
                (mx, y_face + sign * (mag_depth / 2 - 1.0), plate_z / 2)
            )
            cuts.append(c)

    # bottom-face corner mounting magnet bores. Inset kept close to the
    # corner stacking rib/groove (1.85 mm wall between them in X) rather
    # than the plate edge, since the rib/groove -- not the edge -- is the
    # nearest feature at the default stack_inset_x/_y.
    for mx in (bottom_mag_inset_x, plate_x - bottom_mag_inset_x):
        for my in bottom_mag_ys:
            c = trimesh.creation.cylinder(
                radius=mag_d / 2, height=mag_depth + 2, sections=64
            )
            c.apply_translation((mx, my, mag_depth / 2 - 1.0))
            cuts.append(c)

    # corner stacking ribs (top face) and grooves (bottom face): a plate's
    # own top rib seats in the next plate's bottom groove, at the same
    # fixed corner position on every plate regardless of pocket layout.
    # Four corners, inset stack_inset_x/stack_inset_y from each corner --
    # independent of the bottom mounting magnets' Y position, though both
    # stay clear of each other (verified: disjoint footprints at the
    # defaults).
    for mx in stack_xs:
        for my in stack_ys:
            marks.append(
                bx(
                    mx - stack_len / 2, my - stack_w / 2, plate_z - 0.2,
                    mx + stack_len / 2, my + stack_w / 2, plate_z + stack_h,
                )
            )
            scribes.append(
                bx(
                    mx - (stack_len + stack_play) / 2,
                    my - (stack_w + stack_play) / 2, -0.1,
                    mx + (stack_len + stack_play) / 2,
                    my + (stack_w + stack_play) / 2,
                    stack_h,
                )
            )

    # ---- debossed branding on top face (front frame edge) ----
    _front_cy = front_margin / 2

    _tp0 = _text_polys(label, 4.0, 0, 0)
    if not _tp0:
        raise ValueError(
            f"label {label!r} produces no renderable glyphs in the "
            "debossed font (DejaVu Sans) -- e.g. zero-width characters "
            "that pass a whitespace check but still render nothing"
        )
    _tb = [p.bounds for p in _tp0]
    _tw = max(b[2] for b in _tb) - min(b[0] for b in _tb)
    _tx0 = min(b[0] for b in _tb)
    _lw = 6.0
    _total = _lw + 3.0 + _tw
    _sx = (plate_x - _total) / 2

    if _total > plate_y or _total > plate_x:
        raise ValueError(
            f"branding (logo + label {label!r}) is {_total:.1f} mm wide, "
            f"wider than plate_y ({plate_y}) or plate_x ({plate_x}) -- "
            "shorten the label or enlarge the plate"
        )
    _logo_b0 = _logo_polys(0, 0)
    _logo_y0 = min(p.bounds[1] for p in _logo_b0)
    _logo_y1 = max(p.bounds[3] for p in _logo_b0)
    _text_y0 = min(b[1] for b in _tb)
    _text_y1 = max(b[3] for b in _tb)
    _side_logo_cy = plate_z / 2 + 0.4
    _side_text_cy = plate_z / 2 - 2.0
    _branding_z0 = min(_side_logo_cy + _logo_y0, _side_text_cy + _text_y0)
    _branding_z1 = max(_side_logo_cy + _logo_y1, _side_text_cy + _text_y1)
    if _branding_z0 < 0 or _branding_z1 > plate_z:
        raise ValueError(
            f"side-face branding (logo + label {label!r}) spans Z "
            f"[{_branding_z0:.2f}, {_branding_z1:.2f}] mm, which doesn't "
            f"fit within the plate's thickness [0, {plate_z}] -- increase "
            "plate_z"
        )

    _add_deboss(_logo_polys(_sx + _lw / 2, _front_cy + 0.4), scribes,
                plate_z, deboss_d)
    _add_deboss(_text_polys(label, 4.0, _sx + _lw + 3.0 - _tx0, _front_cy - 2.0),
                scribes, plate_z, deboss_d)

    _sx_left = (plate_y - _total) / 2

    _add_deboss_left(_logo_polys(_sx_left + _lw / 2, plate_z / 2 + 0.4),
                      scribes, plate_y, deboss_d)
    _add_deboss_left(
        _text_polys(label, 4.0, _sx_left + _lw + 3.0 - _tx0, plate_z / 2 - 2.0),
        scribes, plate_y, deboss_d,
    )

    _add_deboss_right(_logo_polys(_sx_left + _lw / 2, plate_z / 2 + 0.4),
                       scribes, plate_x, plate_y, deboss_d)
    _add_deboss_right(
        _text_polys(label, 4.0, _sx_left + _lw + 3.0 - _tx0, plate_z / 2 - 2.0),
        scribes, plate_x, plate_y, deboss_d,
    )

    plate = bx(0, 0, 0, plate_x, plate_y, plate_z)
    solid = trimesh.boolean.difference([plate] + cuts, engine="manifold")
    solid = trimesh.boolean.union([solid] + marks, engine="manifold")
    solid = trimesh.boolean.difference([solid] + scribes, engine="manifold")

    geometry = PlateGeometry(
        plate_x=plate_x, plate_y=plate_y, plate_z=plate_z,
        front_margin=front_margin, back_margin=back_margin,
        mag_d=mag_d, mag_depth=mag_depth, mag_xs=mag_xs,
        bottom_mag_inset_x=bottom_mag_inset_x, bottom_mag_ys=bottom_mag_ys,
        stack_w=stack_w, stack_len=stack_len, stack_h=stack_h,
        stack_play=stack_play, stack_inset_x=stack_inset_x,
        stack_inset_y=stack_inset_y,
        stack_xs=stack_xs, stack_ys=stack_ys,
        label=label, deboss_d=deboss_d,
    )
    return PlateResult(solid=solid, geometry=geometry)
