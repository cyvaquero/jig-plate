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
import math
import numbers

import numpy as np
import trimesh
from trimesh.creation import box, extrude_polygon
from shapely.geometry import Polygon, MultiPolygon


_MIN_WALL = 0.8  # ~2 perimeters at a common 0.4mm nozzle
# smallest feature sizes build_plate() accepts (see its input validation)
_MIN_DEBOSS_D = 0.2   # one layer at a common 0.2mm layer height
_MIN_STACK_PLAY = 0.1  # 0 is a press fit that won't seat on FDM prints


@dataclasses.dataclass(frozen=True)
class PlateGeometry:
    """Every position a pocket-layout script needs to build on top of the
    plate without colliding with its magnet bores or stacking rib/groove.

    `front_margin` and `back_margin` are the widths (Y, mm) of the border
    bands along the front and back faces. Pocket-layout scripts use them
    to keep pockets out of the bands that house the mounting magnets and
    branding; `back_margin` positions the back-corner mounting bores
    (`bottom_mag_ys`) and is the back band's width for a pocket layout
    that needs it. `top_branding_bounds` is the footprint
    (x0, y0, x1, y1, mm) of the debossed logo and label on the top face,
    which lies inside the front band."""

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
    top_branding_bounds: tuple = None


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


def _text_width(text, size):
    """Width in mm of `text` set `size` mm tall in the label font: a linear
    measurement that renders no outlines, so it is cheap for any length."""
    from matplotlib.textpath import text_to_path as _t2p
    fp = _label_font_properties()
    w, _h, _d = _t2p.get_text_width_height_descent(text, fp, ismath=False)
    return w * size / fp.get_size_in_points()


def _inked_span(text):
    """`text` without its leading and trailing characters that render no
    outline (spaces, no-break and other fixed-width spaces, U+2800, the
    zero-width characters): they have an advance but no ink, and the
    deboss footprint is measured from the ink. Whether a character has ink
    is decided with _text_polys itself, once per distinct character, so
    this can never keep less than the exact check measures."""
    inked = {}
    for ch in set(text):
        inked[ch] = bool(_text_polys(ch, 4.0, 0, 0))
    first = next((i for i, ch in enumerate(text) if inked[ch]), None)
    if first is None:
        return ""
    last = max(i for i in range(len(text) - 1, first - 1, -1)
               if inked[text[i]])
    return text[first:last + 1]


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


def _is_bool(value):
    """True for `bool` and `np.bool_` (which is not a `bool` subclass).

    numpy does not register `np.bool_` as a `numbers.Real`, so the number
    checks reject it anyway; it is named here so that stays true if that changes.
    """
    return isinstance(value, (bool, np.bool_))


def _native(value):
    """A plain Python `int` or `float`; builtin ints and floats pass through."""
    if type(value) in (int, float):
        return value
    return float(value)


def build_plate(
    *,
    plate_x=246.0, plate_y=218.0, plate_z=9.0,
    front_margin=10.0, back_margin=10.0,
    mag_d=6.1, mag_depth=3.2, mag_count_x=4, mag_inset_x=30.75,
    bottom_mag_inset_x=12.0,
    stack_w=1.5, stack_len=6.0, stack_h=1.5, stack_play=0.2,
    stack_inset_x=4.0, stack_inset_y=4.0,
    label="Jig Plate", deboss_d=0.3, side_branding=True,
):
    """Build the jig plate base solid.

    No pockets -- magnet bores (front/back + bottom-corner mounting) and
    the corner stacking rib/groove system only, plus the debossed logo and
    text label. This is the base every blank-specific pocket layout builds
    on top of; see `PlateGeometry` on the result for where those reserved
    zones are so pockets can avoid them.

    `build_plate()` with no arguments reproduces the current default plate
    exactly. For what the defaults are and why, see the 3.0.0 entry in
    CHANGELOG.md and the `Changelog` block in jig-plate.py's module
    docstring (the per-iteration record).

    `stack_play` gives the rib/groove fit clearance on all three axes, but
    not symmetrically: X and Y split it in half, `stack_play / 2` per side,
    since the rib can land off-center in the groove either way; Z applies
    it in full, since the groove only has one closed side -- its floor --
    for the rib to bottom out against, while the other "side" is the open
    mouth at the plate's bottom face, which needs no clearance of its own.

    Feature sizes must be printable, or `ValueError` is raised naming the
    parameter and its minimum: `mag_d`, `mag_depth`, `stack_w`, `stack_len`
    and `stack_h` >= 0.8 mm (about two perimeters at a 0.4 mm nozzle),
    `deboss_d` >= 0.2 mm (one layer at a 0.2 mm layer height), and
    `stack_play` >= 0.1 mm (0 is a press fit that won't seat on FDM
    prints).

    `side_branding` (default True) debosses the logo and label on the left
    and right faces as well as the top face. Those side marks are a fixed
    size (a 4 mm label beside a taller logo, about 5.8 mm in all), so they
    need a `plate_z` of roughly 7.4 mm or more; below that pass
    `side_branding=False` (the default 6.1 mm bores need about 7.7 mm, so
    a thinner plate also needs a smaller `mag_d`/`mag_depth`). With False,
    the left and right faces stay flat, and there is no side-face Z-fit
    check or side-face keep-out box. The top-face branding is unaffected.
    A non-bool value raises `ValueError`.

    Returns a `PlateResult` (`.solid`: trimesh.Trimesh, `.geometry`:
    PlateGeometry). Pure -- no file I/O, no argv, no printing.
    """
    # ---- input validation -----------------------------------------
    # Type/finiteness/sign checks first (a bad type or a nonsensical
    # negative/zero size fails fast, with its own clear message, rather
    # than surfacing as a collision against something else below).
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

    if not isinstance(side_branding, bool):
        raise ValueError(
            f"side_branding must be a bool, got {side_branding!r}"
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
        if _is_bool(_value) or not isinstance(_value, numbers.Real):
            raise ValueError(f"{_name} must be a number, got {_value!r}")
        # math.isfinite, not np.isfinite: it accepts any int, and raises
        # OverflowError for one too large for a float (10**400), which
        # must be a ValueError naming the parameter like any other bad value
        try:
            _finite = math.isfinite(_value)
        except OverflowError:
            _finite = False
        if not _finite:
            raise ValueError(
                f"{_name} must be finite, got {_value!r:.40}")
    if _is_bool(mag_count_x) or not isinstance(mag_count_x, numbers.Integral):
        raise ValueError(f"mag_count_x must be an int, got {mag_count_x!r}")
    # numpy scalars (np.float32, np.int64) pass the checks above; hand the
    # geometry plain Python numbers so float32 arithmetic can't leak in
    (plate_x, plate_y, plate_z, mag_d, mag_depth, mag_inset_x,
     bottom_mag_inset_x, front_margin, back_margin, stack_w, stack_len,
     stack_h, stack_play, stack_inset_x, stack_inset_y, deboss_d) = (
        _native(v) for v in (
            plate_x, plate_y, plate_z, mag_d, mag_depth, mag_inset_x,
            bottom_mag_inset_x, front_margin, back_margin, stack_w,
            stack_len, stack_h, stack_play, stack_inset_x, stack_inset_y,
            deboss_d))
    mag_count_x = int(mag_count_x)

    if plate_x <= 0 or plate_y <= 0 or plate_z <= 0:
        raise ValueError(
            f"plate_x/plate_y/plate_z must be positive, got "
            f"({plate_x}, {plate_y}, {plate_z})"
        )
    # every dimension that sizes an actual cut/mark feature must reach a
    # printable minimum, or that feature silently vanishes or prints as
    # nothing (mag_depth=0 cuts no bore at all, stack_h=0.05 leaves a rib
    # no printer can lay down, deboss_d=0.001 debosses nothing visible)
    # rather than failing -- caught here, not by the collision check
    # below, since a near-zero-size feature never overlaps anything.
    # Anything below the minimum (zero and negative included) is rejected.
    for _name, _value, _min, _why in (
        ("mag_d", mag_d, _MIN_WALL, "minimum printable feature"),
        ("mag_depth", mag_depth, _MIN_WALL, "minimum printable feature"),
        ("stack_w", stack_w, _MIN_WALL, "minimum printable feature"),
        ("stack_len", stack_len, _MIN_WALL, "minimum printable feature"),
        ("stack_h", stack_h, _MIN_WALL, "minimum printable feature"),
        ("deboss_d", deboss_d, _MIN_DEBOSS_D,
         "one layer at a common 0.2 mm layer height"),
    ):
        if _value < _min:
            raise ValueError(
                f"{_name} must be >= {_min} mm ({_why}), got {_value}"
            )
    if front_margin < 0 or back_margin < 0:
        raise ValueError(
            f"front_margin/back_margin must be >= 0, got "
            f"({front_margin}, {back_margin})"
        )
    if mag_count_x < 2:
        raise ValueError(
            f"mag_count_x ({mag_count_x}) must be >= 2 -- the bore-spacing "
            "formula divides by (mag_count_x - 1)"
        )
    if stack_play < _MIN_STACK_PLAY:
        raise ValueError(
            f"stack_play must be >= {_MIN_STACK_PLAY} mm (fit clearance), "
            f"got {stack_play}: below 0 the groove is cut narrower and "
            "shallower than the rib it has to receive -- two plates "
            "couldn't stack -- and at 0 it is a press fit that won't seat "
            "on FDM prints"
        )
    # the bores and ribs are laid out from each side toward the middle, so
    # an inset at or past half the plate crosses them over (descending
    # positions) or stacks them on one spot
    for _name, _value in (("mag_inset_x", mag_inset_x),
                          ("stack_inset_x", stack_inset_x)):
        if _value >= plate_x / 2:
            raise ValueError(
                f"{_name} ({_value}) must be less than half of plate_x "
                f"({plate_x / 2})"
            )
    if plate_x > 246.0:
        raise ValueError(
            f"plate_x ({plate_x}) exceeds 246 mm (bed width + purge-area "
            "clearance -- see CLAUDE.md)"
        )

    mag_xs = tuple(
        mag_inset_x + i * (plate_x - 2 * mag_inset_x) / (mag_count_x - 1)
        for i in range(mag_count_x)
    )
    bottom_mag_ys = (front_margin / 2, plate_y - back_margin / 2)
    stack_xs = (stack_inset_x, plate_x - stack_inset_x)
    stack_ys = (stack_inset_y, plate_y - stack_inset_y)

    # ---- debossed branding footprint (computed before the geometry
    # check below, so the logo+label cuts can be validated the same way
    # as every mechanical feature -- a long label at a shallow deboss_d
    # can reach sideways into a magnet bore, and deboss_d alone (with no
    # upper limit) can cut the top-face branding all the way through the
    # plate; neither was checked before) ----
    _front_cy = front_margin / 2

    # Cheap length check before any glyph is rendered and nested (that is
    # quadratic in the glyph count, so a very long label stalled for
    # seconds before the width check below rejected it). It rejects only a
    # label whose inked part is wider than plate_x itself, while branding
    # needs the text plus 9 mm of logo and gap to fit, so it can never
    # reject a label that builds; the exact check below stays.
    # measured over the inked span only: leading/trailing characters with
    # no outline cost nothing in the exact check below
    _est_w = _text_width(_inked_span(label), 4.0)
    _shown = label if len(label) <= 40 else label[:40] + "..."
    if _est_w > plate_x:
        raise ValueError(
            f"branding (logo + label {_shown!r}) is far wider than "
            f"plate_x ({plate_x}): the inked part of the label is {_est_w:.0f} mm "
            "wide -- shorten the label or enlarge the plate"
        )

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
    _sx_left = (plate_y - _total) / 2

    # Kept although the feature-box checks below also reject an
    # over-wide branding: this message names the label and the limits.
    # plate_y bounds it only when the side faces carry it too.
    if _total > plate_x or (side_branding and _total > plate_y):
        _limits = (f"plate_x ({plate_x})" if not side_branding else
                   f"plate_y ({plate_y}) or plate_x ({plate_x})")
        raise ValueError(
            f"branding (logo + label {label!r}) is {_total:.1f} mm wide, "
            f"wider than {_limits} -- shorten the label or enlarge the plate"
        )

    # each face's actual logo+text polygons, computed once and reused
    # both for the geometry check below and for the real cuts later --
    # not recomputed, so what's validated is exactly what's cut.
    _top_logo = _logo_polys(_sx + _lw / 2, _front_cy + 0.4)
    _top_text = _text_polys(label, 4.0, _sx + _lw + 3.0 - _tx0, _front_cy - 2.0)
    _top_all = _top_logo + _top_text
    _top_x0 = min(p.bounds[0] for p in _top_all)
    _top_x1 = max(p.bounds[2] for p in _top_all)
    _top_y0 = min(p.bounds[1] for p in _top_all)
    _top_y1 = max(p.bounds[3] for p in _top_all)

    # left/right faces deboss the *same* logo+text polygons (see
    # _add_deboss_left/_add_deboss_right below) through different
    # transforms, so only one pair needs computing.
    _side_logo = _side_text = []
    if side_branding:
        _side_logo = _logo_polys(_sx_left + _lw / 2, plate_z / 2 + 0.4)
        _side_text = _text_polys(
            label, 4.0, _sx_left + _lw + 3.0 - _tx0, plate_z / 2 - 2.0
        )
        _side_all = _side_logo + _side_text
        _side_x0 = min(p.bounds[0] for p in _side_all)  # -> world Y
        _side_x1 = max(p.bounds[2] for p in _side_all)
        _side_z0 = min(p.bounds[1] for p in _side_all)  # -> world Z directly
        _side_z1 = max(p.bounds[3] for p in _side_all)

        # Kept although the feature-box check below also rejects these cases
        # (a Z overrun trips the 0.8 mm wall test on the side-face branding
        # box): this one names the cause (increase plate_z) instead of a
        # generic containment failure.
        if _side_z0 < 0 or _side_z1 > plate_z:
            raise ValueError(
                f"side-face branding (logo + label {label!r}) spans Z "
                f"[{_side_z0:.2f}, {_side_z1:.2f}] mm, which doesn't "
                f"fit within the plate's thickness [0, {plate_z}] -- increase "
                "plate_z"
            )

    # Every mechanical feature (magnet bores, stacking rib/groove,
    # debossed branding) as an axis-aligned bounding box, checked for
    # (a) staying within the plate's own bounds -- with at least
    # _MIN_WALL of material left, not just non-negative -- on every axis
    # where it isn't deliberately supposed to reach or cross one (a
    # blind bore's mouth sits exactly at the face it's drilled from; the
    # rib deliberately stands proud above the top face), and (b) not
    # coming within _MIN_WALL of any other feature. Bounding boxes
    # around the round bores (and the irregular debossed glyph shapes)
    # are a conservative approximation -- it can reject a few diagonal
    # near-misses that would actually clear, but it can never miss a
    # real collision, which is the property that matters here. This one
    # mechanism is what catches every reported "still builds a broken/
    # overlapping/paper-thin-walled plate" case, independent of *which*
    # parameter combination causes it, so a new one doesn't need a new
    # bespoke check.
    # `touch` names which of this feature's own boundaries is deliberately
    # anchored flush to a plate face (a blind bore's mouth, at the face
    # it's drilled from; the branding's cut depth, at the face it's
    # debossed into) -- equality is fine there, no _MIN_WALL required.
    # Every other boundary must keep _MIN_WALL clear of the far face, or
    # the cut leaves less material there than can reliably print, which
    # is just as broken as overshooting it outright.
    _features = []  # (name, (x0,y0,z0,x1,y1,z1), bounds_or_None, touch_set)
    _plate_bounds = (0.0, 0.0, 0.0, plate_x, plate_y, plate_z)
    for _mx in mag_xs:
        _features.append((
            f"front push-fit bore @x={_mx:.2f}",
            (_mx - mag_d / 2, 0.0, plate_z / 2 - mag_d / 2,
             _mx + mag_d / 2, mag_depth, plate_z / 2 + mag_d / 2),
            _plate_bounds, {"y_min"},
        ))
        _features.append((
            f"back push-fit bore @x={_mx:.2f}",
            (_mx - mag_d / 2, plate_y - mag_depth, plate_z / 2 - mag_d / 2,
             _mx + mag_d / 2, plate_y, plate_z / 2 + mag_d / 2),
            _plate_bounds, {"y_max"},
        ))
    for _mx in (bottom_mag_inset_x, plate_x - bottom_mag_inset_x):
        for _my in bottom_mag_ys:
            _features.append((
                f"bottom-corner mounting bore @({_mx:.2f}, {_my:.2f})",
                (_mx - mag_d / 2, _my - mag_d / 2, 0.0,
                 _mx + mag_d / 2, _my + mag_d / 2, mag_depth),
                _plate_bounds, {"z_min"},
            ))
    for _mx in stack_xs:
        for _my in stack_ys:
            # the rib stands proud above the top face by design, so its
            # containment check has no Z-upper-bound
            _features.append((
                f"stacking rib @({_mx:.2f}, {_my:.2f})",
                (_mx - stack_len / 2, _my - stack_w / 2, plate_z,
                 _mx + stack_len / 2, _my + stack_w / 2, plate_z + stack_h),
                (0.0, 0.0, 0.0, plate_x, plate_y, None), set(),
            ))
            # stack_play splits across X and Y (play/2 per side) since the
            # rib can land off-center in the groove on either axis -- but
            # applies in full to Z, since the groove only has one closed
            # side (its floor) for the rib to bottom out against; the
            # other "side" is the open mouth at the plate's bottom face,
            # which needs no clearance of its own.
            _features.append((
                f"stacking groove @({_mx:.2f}, {_my:.2f})",
                (_mx - (stack_len + stack_play) / 2,
                 _my - (stack_w + stack_play) / 2, 0.0,
                 _mx + (stack_len + stack_play) / 2,
                 _my + (stack_w + stack_play) / 2, stack_h + stack_play),
                _plate_bounds, {"z_min"},
            ))
    _features.append((
        f"top-face branding (logo + label {label!r})",
        (_top_x0, _top_y0, plate_z - deboss_d, _top_x1, _top_y1, plate_z),
        _plate_bounds, {"z_max"},
    ))
    if side_branding:
        _features.append((
            f"left-face branding (logo + label {label!r})",
            (0.0, plate_y - _side_x1, _side_z0,
             deboss_d, plate_y - _side_x0, _side_z1),
            _plate_bounds, {"x_min"},
        ))
        _features.append((
            f"right-face branding (logo + label {label!r})",
            (plate_x - deboss_d, _side_x0, _side_z0,
             plate_x, _side_x1, _side_z1),
            _plate_bounds, {"x_max"},
        ))

    _eps = 1e-6  # floating-point noise only, on boundaries allowed to touch

    def _bound_ok(lo, hi, blo, bhi, touch_lo, touch_hi):
        lo_ok = lo >= blo - _eps if touch_lo else lo >= blo + _MIN_WALL - _eps
        hi_ok = hi <= bhi + _eps if touch_hi else hi <= bhi - _MIN_WALL + _eps
        return lo_ok and hi_ok

    for _name, _box, _bounds, _touch in _features:
        if _bounds is None:
            continue
        _x0, _y0, _z0, _x1, _y1, _z1 = _box
        _bx0, _by0, _bz0, _bx1, _by1, _bz1 = _bounds
        if not _bound_ok(_x0, _x1, _bx0, _bx1,
                          "x_min" in _touch, "x_max" in _touch):
            raise ValueError(
                f"{_name} extends past the plate's left/right edge, or "
                f"leaves less than {_MIN_WALL}mm of material there "
                f"(X {_x0:.2f}..{_x1:.2f}, plate is 0..{_bx1:.2f})"
            )
        if not _bound_ok(_y0, _y1, _by0, _by1,
                          "y_min" in _touch, "y_max" in _touch):
            raise ValueError(
                f"{_name} extends past the plate's front/back edge, or "
                f"leaves less than {_MIN_WALL}mm of material there "
                f"(Y {_y0:.2f}..{_y1:.2f}, plate is 0..{_by1:.2f})"
            )
        if _bz1 is None:
            # no upper Z bound (the rib stands proud); same _eps handling
            # as every other bound via an infinite upper limit
            if not _bound_ok(_z0, _z1, _bz0, np.inf,
                              "z_min" in _touch, True):
                raise ValueError(
                    f"{_name} extends below the bottom face "
                    f"(Z min {_z0:.2f})"
                )
        elif not _bound_ok(_z0, _z1, _bz0, _bz1,
                            "z_min" in _touch, "z_max" in _touch):
            raise ValueError(
                f"{_name} extends past the top or bottom face, or "
                f"leaves less than {_MIN_WALL}mm of material there "
                f"(Z {_z0:.2f}..{_z1:.2f}, plate is 0..{_bz1:.2f})"
            )

    for _i in range(len(_features)):
        _name_a, _box_a, _, _ = _features[_i]
        _ax0, _ay0, _az0, _ax1, _ay1, _az1 = _box_a
        for _j in range(_i + 1, len(_features)):
            _name_b, _box_b, _, _ = _features[_j]
            _bx0, _by0, _bz0, _bx1, _by1, _bz1 = _box_b
            # per-axis separation (negative = actual overlap on that
            # axis); if the *best* axis doesn't clear _MIN_WALL, the two
            # features are too close on every axis simultaneously, i.e.
            # they either overlap outright or leave too thin a wall.
            _gap_x = max(_ax0 - _bx1, _bx0 - _ax1)
            _gap_y = max(_ay0 - _by1, _by0 - _ay1)
            _gap_z = max(_az0 - _bz1, _bz0 - _az1)
            if max(_gap_x, _gap_y, _gap_z) < _MIN_WALL - _eps:
                raise ValueError(
                    f"{_name_a} comes within {_MIN_WALL}mm of {_name_b} "
                    "(or overlaps it)"
                )

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
            # stack_play: half per side in X/Y, full in Z -- see the
            # matching comment on the groove's feature-check box above.
            scribes.append(
                bx(
                    mx - (stack_len + stack_play) / 2,
                    my - (stack_w + stack_play) / 2, -0.1,
                    mx + (stack_len + stack_play) / 2,
                    my + (stack_w + stack_play) / 2,
                    stack_h + stack_play,
                )
            )

    # ---- debossed branding cuts (top; left/right when side_branding) --
    # reusing the exact polygons already validated above, not recomputed ----
    _add_deboss(_top_logo, scribes, plate_z, deboss_d)
    _add_deboss(_top_text, scribes, plate_z, deboss_d)
    if side_branding:
        _add_deboss_left(_side_logo, scribes, plate_y, deboss_d)
        _add_deboss_left(_side_text, scribes, plate_y, deboss_d)
        _add_deboss_right(_side_logo, scribes, plate_x, plate_y, deboss_d)
        _add_deboss_right(_side_text, scribes, plate_x, plate_y, deboss_d)

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
        top_branding_bounds=(_top_x0, _top_y0, _top_x1, _top_y1),
    )
    return PlateResult(solid=solid, geometry=geometry)
