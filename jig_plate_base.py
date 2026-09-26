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
    mag_xs: list
    bottom_mag_inset_x: float
    bottom_mag_ys: list
    stack_w: float
    stack_len: float
    stack_h: float
    stack_play: float
    stack_inset_x: float
    stack_xs: tuple
    stack_ys: list
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


def build_plate(
    *,
    plate_x=246.0, plate_y=218.0, plate_z=9.0,
    front_margin=10.0, back_margin=10.0,
    mag_d=6.1, mag_depth=3.2, mag_count_x=4, mag_inset_x=30.75,
    bottom_mag_inset_x=20.0,
    stack_w=1.5, stack_len=6.0, stack_h=1.5, stack_play=0.2,
    stack_inset_x=6.0,
    label="Jig Plate", deboss_d=0.3,
):
    """Build the jig plate base solid.

    No pockets -- magnet bores (front/back + bottom-corner mounting) and
    the corner stacking rib/groove system only, plus the debossed logo and
    text label. This is the base every blank-specific pocket layout builds
    on top of; see `PlateGeometry` on the result for where those reserved
    zones are so pockets can avoid them.

    All defaults match the original single-script generator (v1.1.0), so
    `build_plate()` with no arguments reproduces that plate exactly.

    Returns a `PlateResult` (`.solid`: trimesh.Trimesh, `.geometry`:
    PlateGeometry). Pure -- no file I/O, no argv, no printing.
    """
    mag_xs = [
        mag_inset_x + i * (plate_x - 2 * mag_inset_x) / (mag_count_x - 1)
        for i in range(mag_count_x)
    ]
    bottom_mag_ys = [front_margin / 2, plate_y - back_margin / 2]
    stack_xs = (stack_inset_x, plate_x - stack_inset_x)
    stack_ys = bottom_mag_ys

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

    # bottom-face corner mounting magnet bores
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
    # Four corners, same Y bands as the bottom magnets.
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
                    mx - stack_len / 2, my - (stack_w + stack_play) / 2, -0.1,
                    mx + stack_len / 2, my + (stack_w + stack_play) / 2,
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
        stack_xs=stack_xs, stack_ys=stack_ys,
        label=label, deboss_d=deboss_d,
    )
    return PlateResult(solid=solid, geometry=geometry)
