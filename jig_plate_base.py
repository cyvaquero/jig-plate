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
from shapely.geometry import Polygon, MultiPolygon, box as shapely_box
from shapely.ops import unary_union


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
    mag_xs: list
    bottom_mag_inset_x: float
    bottom_mag_ys: list
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
    honeycomb_enabled: bool
    honeycomb_skin: float
    honeycomb_wall: float
    honeycomb_af: float
    honeycomb_margin_x: float
    honeycomb_margin_y: float


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


def _text_polys(text, size, x0, y0):
    """Shapely polygons for extrudable text at (x0, y0) baseline."""
    from matplotlib.textpath import TextPath as _TP
    from matplotlib.font_manager import FontProperties as _FP
    # pinned to the font matplotlib bundles internally (not a system font),
    # so the debossed text is identical on macOS, Windows, and Linux
    tp = _TP((x0, y0), text, size=size,
             prop=_FP(family="DejaVu Sans", weight="bold"))
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


def _hex_field_polys(x0, x1, y0, y1, af, wall):
    """Full-coverage pointy-top hex lattice (cell holes only -- the rib is
    the gap left between adjacent holes by the pitch, same construction as
    eu-business-card-jig's vented pocket floor), covering at least the
    [x0, x1] x [y0, y1] rectangle so it can be clipped to it afterward."""
    Rh = af / np.sqrt(3.0)  # hole circumradius
    Rc = (af + wall) / np.sqrt(3.0)  # cell (hole + rib) circumradius
    col_p = af + wall
    row_p = 1.5 * Rc
    base = [
        (Rh * np.cos(np.radians(90 + 60 * k)), Rh * np.sin(np.radians(90 + 60 * k)))
        for k in range(6)
    ]

    polys = []
    r = 0
    cy = y0 - Rh
    while cy <= y1 + Rh + 1e-9:
        cx = x0 - af / 2 + (col_p / 2 if r % 2 else 0.0)
        while cx <= x1 + af / 2 + 1e-9:
            polys.append(Polygon([(cx + vx, cy + vy) for vx, vy in base]))
            cx += col_p
        cy += row_p
        r += 1
    return polys


def _honeycomb_cuts(
    plate_x, plate_y, plate_z,
    honeycomb_skin, honeycomb_wall, honeycomb_af,
    honeycomb_margin_x, honeycomb_margin_y,
    bottom_mag_inset_x, bottom_mag_ys, mag_d,
    stack_xs, stack_ys, stack_w, stack_len,
):
    """Bottom-face honeycomb lightening cutout: a hex grid of blind pockets
    cut up from z=0, leaving a thin skin at the top and a honeycomb wall
    between pockets.

    Built as a full lattice then clipped to the margin-inset field with a
    boolean intersection, so boundary cells are cut short rather than
    dropped whole -- same approach eu-business-card-jig uses for its
    vented pocket floor. The clipped field is then subtracted from the
    bottom-corner mount-bore and corner-stack-rib/groove footprints (with
    clearance) so a cell reaching into either gets clipped there too,
    instead of relying on the margins alone to keep clear. Any sliver left
    over from either clip that's too small to print cleanly is dropped.
    """
    cuts = []
    x0, x1 = honeycomb_margin_x, plate_x - honeycomb_margin_x
    y0, y1 = honeycomb_margin_y, plate_y - honeycomb_margin_y
    if x1 <= x0 or y1 <= y0:
        return cuts

    pocket_top_z = plate_z - honeycomb_skin  # cut from the bottom up to here

    field = unary_union(_hex_field_polys(x0, x1, y0, y1, honeycomb_af, honeycomb_wall))
    field = field.intersection(shapely_box(x0, y0, x1, y1))

    excl = []
    mag_r = mag_d / 2 + 2.0
    for mx in (bottom_mag_inset_x, plate_x - bottom_mag_inset_x):
        for my in bottom_mag_ys:
            excl.append(shapely_box(mx - mag_r, my - mag_r, mx + mag_r, my + mag_r))
    stack_clear = 2.0
    for sx in stack_xs:
        for sy in stack_ys:
            excl.append(shapely_box(
                sx - stack_len / 2 - stack_clear, sy - stack_w / 2 - stack_clear,
                sx + stack_len / 2 + stack_clear, sy + stack_w / 2 + stack_clear,
            ))
    if excl:
        field = field.difference(unary_union(excl))

    min_sliver_area = 3.0  # drop fragments too small to print cleanly
    geoms = list(field.geoms) if hasattr(field, "geoms") else [field]
    for g in geoms:
        if not isinstance(g, Polygon) or g.is_empty or g.area < min_sliver_area:
            continue
        cuts.append(extrude_polygon(g, height=pocket_top_z))
    return cuts


def build_plate(
    *,
    plate_x=246.0, plate_y=218.0, plate_z=9.0,
    front_margin=10.0, back_margin=10.0,
    mag_d=6.1, mag_depth=3.2, mag_count_x=4, mag_inset_x=30.75,
    bottom_mag_inset_x=12.0,
    stack_w=1.5, stack_len=6.0, stack_h=1.5, stack_play=0.2,
    stack_inset_x=4.0, stack_inset_y=4.0,
    label="Jig Plate", deboss_d=0.3,
    honeycomb_enabled=True, honeycomb_skin=2.4, honeycomb_wall=2.6,
    honeycomb_af=23.1, honeycomb_margin_x=16.0, honeycomb_margin_y=22.0,
):
    """Build the jig plate base solid.

    No pockets -- magnet bores (front/back + bottom-corner mounting) and
    the corner stacking rib/groove system only, plus the debossed logo and
    text label. This is the base every blank-specific pocket layout builds
    on top of; see `PlateGeometry` on the result for where those reserved
    zones are so pockets can avoid them.

    `build_plate()` with no arguments reproduces the current default plate
    exactly -- see CHANGELOG.md for what the defaults are and why.

    A honeycomb lightening cutout is cut up from the bottom face by
    default (`honeycomb_enabled=True`): a thin `honeycomb_skin`-thick top
    skin left uncut, with a hex grid of pockets (`honeycomb_af` mm across
    flats, same sizing convention as eu-business-card-jig's vented pocket
    floor) separated by `honeycomb_wall`-wide walls, inset
    `honeycomb_margin_x`/`honeycomb_margin_y` from the plate edges. Unlike
    a drop-if-it-doesn't-fit grid, the lattice is clipped to the margin
    field and to the bottom-corner mounting magnet bores/corner stacking
    rib-groove footprints (with clearance) via boolean intersection and
    difference, so boundary cells are cut short rather than omitted -- see
    `_honeycomb_cuts`. Pass `honeycomb_enabled=False` for a solid
    underside.

    Returns a `PlateResult` (`.solid`: trimesh.Trimesh, `.geometry`:
    PlateGeometry). Pure -- no file I/O, no argv, no printing.
    """
    mag_xs = [
        mag_inset_x + i * (plate_x - 2 * mag_inset_x) / (mag_count_x - 1)
        for i in range(mag_count_x)
    ]
    bottom_mag_ys = [front_margin / 2, plate_y - back_margin / 2]
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
    # corner stacking rib/groove (1.95 mm wall between them in X, the same
    # clearance value already used elsewhere in this design) rather than
    # the plate edge, since the rib/groove -- not the edge -- is the
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
                    stack_h + 0.1,
                )
            )

    # ---- debossed branding on top face (front frame edge) ----
    _front_cy = front_margin / 2

    _tp0 = _text_polys(label, 4.0, 0, 0)
    _tb = [p.bounds for p in _tp0]
    _tw = max(b[2] for b in _tb) - min(b[0] for b in _tb)
    _tx0 = min(b[0] for b in _tb)
    _lw = 6.0
    _total = _lw + 3.0 + _tw
    _sx = (plate_x - _total) / 2

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

    if honeycomb_enabled:
        cuts.extend(_honeycomb_cuts(
            plate_x, plate_y, plate_z,
            honeycomb_skin, honeycomb_wall, honeycomb_af,
            honeycomb_margin_x, honeycomb_margin_y,
            bottom_mag_inset_x, bottom_mag_ys, mag_d,
            stack_xs, stack_ys, stack_w, stack_len,
        ))

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
        honeycomb_enabled=honeycomb_enabled, honeycomb_skin=honeycomb_skin,
        honeycomb_wall=honeycomb_wall, honeycomb_af=honeycomb_af,
        honeycomb_margin_x=honeycomb_margin_x, honeycomb_margin_y=honeycomb_margin_y,
    )
    return PlateResult(solid=solid, geometry=geometry)
