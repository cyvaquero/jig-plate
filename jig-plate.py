"""Jig plate -- parametric generator for the stackable laser-jig base plate.

VERSION below is the single source of truth: it drives the output
filenames and the 80-byte binary STL header of both meshes.

This is the base plate only -- no blank-specific pockets. Keeps only what is
blank-agnostic: the magnet bores and the corner stacking rib/groove system.
Pockets for a specific blank are added on top of this base in a separate
script.

Changelog
  0.1.0  base design -- magnet bores and corner stacking rib/groove system,
         debossed "Jig Plate" wordmark, no pocket geometry
  1.0.0  first stable release -- script and documentation reviewed, no
         geometry changes; dead code removed from the stacking-joint
         detail drawing; documentation figure/filename inconsistencies
         corrected
"""
from pathlib import Path

import numpy as np
import trimesh
from trimesh.creation import box, extrude_polygon
from shapely.geometry import Polygon, MultiPolygon
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

VERSION = "1.0.0"
OUT_DIR = Path(__file__).resolve().parent / "output"

# ---------------- parameters (mm) ----------------
PLATE_X, PLATE_Y, PLATE_Z = 246.0, 218.0, 9.0

# border bands along the front (-Y) and back (+Y) edges: house the bottom
# mounting magnets and the corner stacking rib/groove, independent of
# whatever pocket layout gets added on top of this base later
FRONT_MARGIN, BACK_MARGIN = 10.0, 17.0

MAG_D = 6.1  # bore for a 6 mm magnet, push fit
MAG_DEPTH = 3.2  # blind depth for a 3 mm magnet

# push-fit magnet bores in the front (-Y) and back (+Y) faces: evenly spaced
# and symmetric about the X centreline, positioned off PLATE_X only, so
# stacked jigs mate face to face regardless of pocket layout
MAG_COUNT_X = 4
MAG_INSET_X = 30.75  # first/last bore center inset from the left/right edges
MAG_XS = [
    MAG_INSET_X + i * (PLATE_X - 2 * MAG_INSET_X) / (MAG_COUNT_X - 1)
    for i in range(MAG_COUNT_X)
]

# push-fit magnet bores in the four corners of the bottom (-Z) face, for
# mounting the plate itself (e.g. to a magnetic base). Same 6.1 mm bore /
# 3.2 mm depth as the front/back mating magnets, blind from the bottom
# upward. Centered in the front/back border bands, well inset from the
# side edges so the corner stacking rib/groove has clear room next to it.
BOTTOM_MAG_INSET_X = 20.0
BOTTOM_MAG_YS = [FRONT_MARGIN / 2, PLATE_Y - BACK_MARGIN / 2]

# corner stacking ribs/grooves: blank-agnostic registration between two
# plates. Positioned off PLATE_X/PLATE_Y only, so any two plates sharing
# the same outer footprint stack together regardless of what pocket layout
# each one holds.
STACK_W = 1.5  # rib/groove width (Y)
STACK_LEN = 6.0  # rib/groove length (X)
STACK_H = 1.5  # raised height on top face -- prouder than the old pocket
# datum lines were, so the stacking fit carries the alignment load
STACK_PLAY = 0.2  # extra width cut into the receiving groove
STACK_INSET_X = 6.0  # rib/groove center inset from the left/right edges
STACK_XS = (STACK_INSET_X, PLATE_X - STACK_INSET_X)
STACK_YS = BOTTOM_MAG_YS

OUT_DIR.mkdir(exist_ok=True)
OUT = OUT_DIR / f"jig_plate_{VERSION}.stl"


def bx(x0, y0, z0, x1, y1, z1):
    m = box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


cuts, marks, scribes = [], [], []

# push-fit magnet bores in the front (-Y) and back (+Y) faces, same X
# positions on both so stacked plates mate face to face
for mx in MAG_XS:
    for y_face, sign in ((0.0, 1.0), (PLATE_Y, -1.0)):
        c = trimesh.creation.cylinder(
            radius=MAG_D / 2, height=MAG_DEPTH + 2, sections=64
        )
        c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        c.apply_translation((mx, y_face + sign * (MAG_DEPTH / 2 - 1.0), PLATE_Z / 2))
        cuts.append(c)

# bottom-face corner mounting magnet bores
for mx in (BOTTOM_MAG_INSET_X, PLATE_X - BOTTOM_MAG_INSET_X):
    for my in BOTTOM_MAG_YS:
        c = trimesh.creation.cylinder(
            radius=MAG_D / 2, height=MAG_DEPTH + 2, sections=64
        )
        c.apply_translation((mx, my, MAG_DEPTH / 2 - 1.0))
        cuts.append(c)

# corner stacking ribs (top face) and grooves (bottom face): a plate's own
# top rib seats in the next plate's bottom groove, at the same fixed corner
# position on every plate regardless of pocket layout -- see STACK_*
# comments above. Four corners, same Y bands as the bottom magnets.
for mx in STACK_XS:
    for my in STACK_YS:
        marks.append(
            bx(
                mx - STACK_LEN / 2, my - STACK_W / 2, PLATE_Z - 0.2,
                mx + STACK_LEN / 2, my + STACK_W / 2, PLATE_Z + STACK_H,
            )
        )
        scribes.append(
            bx(
                mx - STACK_LEN / 2, my - (STACK_W + STACK_PLAY) / 2, -0.1,
                mx + STACK_LEN / 2, my + (STACK_W + STACK_PLAY) / 2,
                STACK_H + 0.1,
            )
        )

# ---- debossed branding on top face (front frame edge) ----
DEBOSS_D = 0.3
LABEL = "Jig Plate"
_front_cy = FRONT_MARGIN / 2


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
    tp = _TP((x0, y0), text, size=size,
             prop=_FP(family="sans-serif", weight="bold"))
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


def _add_deboss(poly_list, target):
    """Extrude polys as cut volumes and append to target list."""
    for p in poly_list:
        geoms = list(p.geoms) if isinstance(p, MultiPolygon) else [p]
        for g in geoms:
            if g.is_empty or abs(g.area) < 0.01:
                continue
            m = extrude_polygon(g, height=DEBOSS_D + 0.2)
            m.apply_translation((0, 0, PLATE_Z - DEBOSS_D))
            target.append(m)


_tp0 = _text_polys(LABEL, 4.0, 0, 0)
_tb = [p.bounds for p in _tp0]
_tw = max(b[2] for b in _tb) - min(b[0] for b in _tb)
_tx0 = min(b[0] for b in _tb)
_lw = 6.0
_total = _lw + 3.0 + _tw
_sx = (PLATE_X - _total) / 2

_add_deboss(_logo_polys(_sx + _lw / 2, _front_cy + 0.4), scribes)
_add_deboss(_text_polys(LABEL, 4.0,
                        _sx + _lw + 3.0 - _tx0, _front_cy - 2.0), scribes)


def _add_deboss_left(poly_list, target):
    """Deboss on the left face (x=0), readable from outside (-X)."""
    for p in poly_list:
        geoms = list(p.geoms) if isinstance(p, MultiPolygon) else [p]
        for g in geoms:
            if g.is_empty or abs(g.area) < 0.01:
                continue
            m = extrude_polygon(g, height=DEBOSS_D + 0.2)
            verts = m.vertices.copy()
            new_v = np.empty_like(verts)
            new_v[:, 0] = verts[:, 2] - 0.2
            new_v[:, 1] = PLATE_Y - verts[:, 0]
            new_v[:, 2] = verts[:, 1]
            m.vertices = new_v
            m.invert()
            target.append(m)


_sx_left = (PLATE_Y - _total) / 2

_add_deboss_left(_logo_polys(_sx_left + _lw / 2, PLATE_Z / 2 + 0.4), scribes)
_add_deboss_left(_text_polys(LABEL, 4.0,
                             _sx_left + _lw + 3.0 - _tx0,
                             PLATE_Z / 2 - 2.0), scribes)

plate = bx(0, 0, 0, PLATE_X, PLATE_Y, PLATE_Z)
solid = trimesh.boolean.difference([plate] + cuts, engine="manifold")
solid = trimesh.boolean.union([solid] + marks, engine="manifold")
solid = trimesh.boolean.difference([solid] + scribes, engine="manifold")

print(
    "watertight:",
    solid.is_watertight,
    "| volume cm3:",
    round(solid.volume / 1000, 1),
    "| bbox:",
    np.round(solid.bounds[1] - solid.bounds[0], 3),
    "| faces:",
    len(solid.faces),
)

solid.export(OUT)
print("wrote", OUT)


# stamp the 80-byte binary STL header so the version travels with the file
def stamp(path, text):
    b = bytearray(open(path, "rb").read())
    b[0:80] = text.encode("ascii").ljust(80, b"\x00")
    open(path, "wb").write(b)


stamp(
    OUT,
    f"Jig plate {VERSION} | "
    f"{PLATE_X:.0f}x{PLATE_Y:.0f}x{PLATE_Z:.0f}mm | base plate, no pockets",
)

# test coupon: front-right corner, carrying the stacking rib/groove and its
# bottom mounting magnet -- for validating the corner stacking fit
# independently of any pocket layout added later. Print two to test mating.
STACK_COUPON = OUT_DIR / f"jig_plate_{VERSION}_stack_coupon.stl"
SC_X0, SC_Y0, SC_Y1 = PLATE_X - 46.0, 0.0, 20.0
stack_coupon = trimesh.boolean.intersection(
    [solid, bx(SC_X0, SC_Y0, -1, PLATE_X, SC_Y1, PLATE_Z + STACK_H + 1)],
    engine="manifold",
)
stack_coupon.export(STACK_COUPON)
print("wrote", STACK_COUPON)
stamp(
    STACK_COUPON,
    f"Jig plate {VERSION} | "
    f"stack coupon {PLATE_X - SC_X0:g}x{SC_Y1 - SC_Y0:g}x{PLATE_Z:.0f}mm | corner",
)
print(
    "stack coupon:",
    stack_coupon.is_watertight,
    round(stack_coupon.volume / 1000, 2),
    "cm3",
    np.round(stack_coupon.bounds[1] - stack_coupon.bounds[0], 2),
)

# -------- labelled diagram --------
IMG_DIR = Path(__file__).resolve().parent / "images"
IMG_DIR.mkdir(exist_ok=True)

TEAL = "#1D9E75"
AMBER = "#BA7517"
VIOLET = "#7F77DD"
SHAPE = "#888780"
FG = "#1a1915"
MUTED = "#6b6860"
BG = "#faf9f7"

C30, S30 = np.cos(np.radians(30)), np.sin(np.radians(30))


def iso(x, y, z):
    return (C30 * (x - y), -S30 * (x + y) + z)


def iso_rect(x0, y0, x1, y1, z):
    return [iso(x0, y0, z), iso(x1, y0, z), iso(x1, y1, z), iso(x0, y1, z)]


def iso_right_face(x, y0, y1, z0, z1):
    return [iso(x, y0, z0), iso(x, y1, z0), iso(x, y1, z1), iso(x, y0, z1)]


def iso_front_face(x0, x1, y, z0, z1):
    return [iso(x0, y, z0), iso(x1, y, z0), iso(x1, y, z1), iso(x0, y, z1)]


def leader(ax, anchor, text_pos, label, ha="left", dashed=True):
    ax.plot(*anchor, "o", color=FG, ms=3.5, zorder=5)
    ax.plot([anchor[0], text_pos[0]], [anchor[1], text_pos[1]],
            color=MUTED, lw=0.8,
            ls=(0, (3, 2)) if dashed else "-", zorder=4)
    ax.text(text_pos[0], text_pos[1], label, fontsize=8.5,
            fontfamily="sans-serif", color=FG, ha=ha, va="center",
            zorder=6)


def add_key(ax, items, y_pos):
    total_w = sum(len(label) * 5.5 + 22 for label, _ in items)
    x = -total_w / 2
    for label, color in items:
        ax.add_patch(FancyBboxPatch((x, y_pos - 5), 11, 11,
                     boxstyle="round,pad=1", fc=color, ec="none",
                     alpha=0.7, zorder=5))
        ax.text(x + 16, y_pos + 0.5, label, fontsize=7.5,
                color=MUTED, va="center", fontfamily="sans-serif", zorder=5)
        x += len(label) * 5.5 + 30


# ---- plate diagram (isometric) ----
def _plate_diagram(out_path):
    from matplotlib.patches import Polygon as MplPoly, Circle as MplCircle
    S = 1.8
    fig, ax = plt.subplots(figsize=(12, 8.5), dpi=200)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    px, py, pz = PLATE_X * S, PLATE_Y * S, PLATE_Z * S * 3

    ax.add_patch(MplPoly(iso_rect(0, 0, px, py, pz),
                 fc=SHAPE, alpha=0.16, ec=FG, lw=0.5, zorder=2))
    ax.add_patch(MplPoly(iso_right_face(px, 0, py, 0, pz),
                 fc=SHAPE, alpha=0.42, ec=FG, lw=0.5, zorder=2))
    ax.add_patch(MplPoly(iso_front_face(0, px, py, 0, pz),
                 fc=SHAPE, alpha=0.30, ec=FG, lw=0.5, zorder=2))

    # magnet positions on the front edge, for reference
    for mx in MAG_XS:
        mag_pt = iso(mx * S, 0, pz * 0.5)
        ax.add_patch(MplCircle(mag_pt, 3.5, fc=VIOLET, alpha=0.6,
                     ec=FG, lw=0.4, zorder=4))

    # corner stacking rib footprint, top-left-front corner, for reference
    sx0, sy0 = STACK_XS[0] * S, STACK_YS[0] * S
    ax.add_patch(MplPoly(iso_rect(sx0 - STACK_LEN * S / 2, sy0 - STACK_W * S / 2,
                                   sx0 + STACK_LEN * S / 2, sy0 + STACK_W * S / 2, pz),
                 fc=AMBER, alpha=0.7, ec=FG, lw=0.4, zorder=4))

    top_ctr = iso(px / 2, py / 2, pz)
    ax.text(top_ctr[0], top_ctr[1], "Top face",
            fontsize=9, fontweight="semibold", color=FG,
            ha="center", va="center", zorder=6)

    fr_pt = iso(px * 0.7, 0, pz * 0.5)
    leader(ax, fr_pt, (fr_pt[0] + 80, fr_pt[1] - 30),
           "Front edge (magnets)")

    left_pt = iso(0, py * 0.35, pz * 0.7)
    leader(ax, left_pt, (left_pt[0] - 80, left_pt[1] + 30),
           "Left edge (branding)", ha="right")

    right_pt = iso(px, py * 0.55, pz * 0.35)
    leader(ax, right_pt, (right_pt[0] + 80, right_pt[1] + 10),
           "Right edge", dashed=False)

    back_pt = iso(px * 0.25, py, pz * 0.35)
    leader(ax, back_pt, (back_pt[0] - 60, back_pt[1] - 60),
           "Back edge (magnets)", ha="right", dashed=False)

    bottom_pt = iso(px / 2, py, 0)
    leader(ax, bottom_pt, (bottom_pt[0] + 70, bottom_pt[1] - 30),
           "Bottom — sits on the bed, carries mounting magnets")

    mag_pt = iso(MAG_XS[1] * S, 0, pz * 0.5)
    leader(ax, mag_pt, (mag_pt[0] - 30, mag_pt[1] - 55),
           "Magnet bore", ha="right")

    stack_pt = iso(sx0, sy0, pz)
    leader(ax, stack_pt, (stack_pt[0] + 60, stack_pt[1] + 55),
           "Corner stacking rib\n(groove on underside)")

    add_key(ax, [
        ("plate", SHAPE), ("magnets", VIOLET), ("stacking rib", AMBER),
    ], ax.get_ylim()[0] + 15)

    ax.autoscale_view()
    ax.margins(0.08)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", pad_inches=0.3,
                facecolor=BG)
    plt.close(fig)
    print("wrote", out_path)


_plate_diagram(IMG_DIR / f"jig_plate_{VERSION}_diagram.png")


# -------- technical drawings --------
DIM_COLOR = "#333333"
DIM_LW = 0.6
EXT_LW = 0.4
HATCH_COLOR = "#666666"
HATCH_LW = 0.3
CUT_LW = 1.2
HIDDEN_LW = 0.5
HIDDEN_LS = (0, (4, 2))
SECTION_COLOR = TEAL
# dimension text interrupts whatever it crosses, as on a real drawing
_DIM_LABEL_BBOX = dict(facecolor=BG, edgecolor="none", pad=0.15)


def _dim_h(ax, y, x0, x1, label, offset=0, fontsize=7, side="above",
           tick=False):
    # tick=True for spans narrower than a pair of arrowheads, which would
    # otherwise meet in the middle and read as a bowtie
    oy = y + offset
    gap = 1.2 if side == "above" else -1.2
    ax.annotate("", xy=(x0, oy), xytext=(x1, oy),
                arrowprops=dict(arrowstyle="|-|" if tick else "<->",
                                color=DIM_COLOR, lw=DIM_LW,
                                shrinkA=0, shrinkB=0))
    ax.plot([x0, x0], [y, oy], color=DIM_COLOR, lw=EXT_LW)
    ax.plot([x1, x1], [y, oy], color=DIM_COLOR, lw=EXT_LW)
    ax.text((x0 + x1) / 2, oy + gap, label, fontsize=fontsize,
            ha="center", va="bottom" if side == "above" else "top",
            color=DIM_COLOR, fontfamily="sans-serif", zorder=7,
            bbox=_DIM_LABEL_BBOX)


def _dim_v(ax, x, y0, y1, label, offset=0, fontsize=7, side="right"):
    ox = x + offset
    gap = 1.2 if side == "right" else -1.2
    ax.annotate("", xy=(ox, y0), xytext=(ox, y1),
                arrowprops=dict(arrowstyle="<->", color=DIM_COLOR,
                                lw=DIM_LW, shrinkA=0, shrinkB=0))
    ax.plot([x, ox], [y0, y0], color=DIM_COLOR, lw=EXT_LW)
    ax.plot([x, ox], [y1, y1], color=DIM_COLOR, lw=EXT_LW)
    ax.text(ox + gap, (y0 + y1) / 2, label, fontsize=fontsize,
            ha="left" if side == "right" else "right",
            va="center", color=DIM_COLOR, fontfamily="sans-serif",
            rotation=90, zorder=7, bbox=_DIM_LABEL_BBOX)


def _fit_view(*axes, pad=0.05):
    # dataLim tracks patches and lines but never text, so every dimension
    # label sits outside it and naive autoscaling crops them; union the
    # labels' rendered extents in first. Measuring costs a full draw, so
    # fit every axes off the one draw.
    from matplotlib.transforms import Bbox
    fig = axes[0].figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for ax in axes:
        inv = ax.transData.inverted()
        extent = Bbox(ax.dataLim.get_points().copy())
        for label in ax.texts:
            if label.get_transform() is ax.transAxes:
                continue  # captions are pinned to the box on purpose
            box_ = label.get_window_extent(renderer)
            extent = Bbox.union([extent, box_.transformed(inv)])
        dx, dy = extent.width * pad, extent.height * pad
        ax.set_xlim(extent.x0 - dx, extent.x1 + dx)
        ax.set_ylim(extent.y0 - dy, extent.y1 + dy)


def _hatch_fill(ax, clip, cx, cy, diag, angle, spacing):
    # autolim=False: the lines overhang the clip patch by design, and a clip
    # path is applied at draw time only — letting them reach dataLim inflates
    # it to a 45-degree square and collapses any axes that autoscales.
    from matplotlib.collections import LineCollection
    n = int(diag / spacing) + 1
    rad = np.radians(angle)
    cos_a, sin_a = np.cos(rad), np.sin(rad)
    d = np.arange(-n, n + 1) * spacing
    start = np.column_stack([cx + d * cos_a - diag * sin_a,
                             cy + d * sin_a + diag * cos_a])
    end = np.column_stack([cx + d * cos_a + diag * sin_a,
                           cy + d * sin_a - diag * cos_a])
    lc = LineCollection(np.stack([start, end], axis=1), colors=HATCH_COLOR,
                        linewidths=HATCH_LW, zorder=2)
    lc.set_clip_path(clip)
    ax.add_collection(lc, autolim=False)


def _hatch_rect(ax, x0, y0, x1, y1, angle=45, spacing=1.5):
    from matplotlib.patches import Polygon as MplPoly
    clip = MplPoly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True,
                   transform=ax.transData)
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    diag = np.sqrt(dx**2 + dy**2) * 1.5
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    _hatch_fill(ax, clip, cx, cy, diag, angle, spacing)


def _title_block(ax, title, scale_label):
    # below the axes, not inside it: on a wide flat view like the front
    # elevation the box is short enough that an inset caption lands on
    # the drawing
    ax.text(0.99, -0.08, f"{title}  |  v{VERSION}  |  {scale_label}",
            transform=ax.transAxes, fontsize=7, ha="right", va="top",
            color=MUTED, fontfamily="sans-serif")


# ---- technical drawing 1: dimensioned top plan view ----
def _tech_top_plan(out_path):
    from matplotlib.patches import Polygon as MplPoly
    S = 2.0
    fig, ax = plt.subplots(figsize=(14, 10), dpi=200)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # plate outline
    ax.add_patch(plt.Rectangle((0, 0), PLATE_X * S, PLATE_Y * S,
                 fc="none", ec=FG, lw=CUT_LW, zorder=3))

    # magnet bores (front and back faces)
    for mx in MAG_XS:
        for y_face in [0, PLATE_Y]:
            ax.plot(mx * S, y_face * S, "o", color=VIOLET, ms=MAG_D * S / 2,
                    mfc="none", mew=1.0, zorder=5)
            ax.plot(mx * S, y_face * S, "+", color=VIOLET, ms=3, mew=0.6,
                    zorder=5)

    # bottom-face mounting magnets: hidden from this view (underside), so
    # drawn dashed per the hidden-line convention rather than the solid
    # circles used for the front/back through-faces above
    for mx in (BOTTOM_MAG_INSET_X, PLATE_X - BOTTOM_MAG_INSET_X):
        for my in BOTTOM_MAG_YS:
            ax.add_patch(plt.Circle((mx * S, my * S), MAG_D * S / 2,
                         fc="none", ec=VIOLET, lw=HIDDEN_LW, ls=HIDDEN_LS,
                         zorder=5))
            ax.plot(mx * S, my * S, "+", color=VIOLET, ms=3, mew=0.6,
                    zorder=5)

    # corner stacking ribs (top face, visible) / grooves (bottom, hidden
    # underneath at the same footprint plus play)
    for mx in STACK_XS:
        for my in STACK_YS:
            ax.add_patch(plt.Rectangle(
                (mx * S - STACK_LEN * S / 2, my * S - STACK_W * S / 2),
                STACK_LEN * S, STACK_W * S,
                fc=AMBER, alpha=0.6, ec=FG, lw=0.6, zorder=5))

    # overall dimensions
    _dim_h(ax, PLATE_Y * S, 0, PLATE_X * S,
           f"{PLATE_X:.0f}", offset=12 * S)
    _dim_v(ax, PLATE_X * S, 0, PLATE_Y * S,
           f"{PLATE_Y:.0f}", offset=12 * S)

    # front border band (houses the bottom mounting magnet + branding)
    _dim_v(ax, 0, 0, FRONT_MARGIN * S,
           f"{FRONT_MARGIN:.0f}", offset=-15 * S, side="left")

    # magnet X positions
    ax.annotate("", xy=(MAG_XS[0] * S, -6 * S), xytext=(MAG_XS[1] * S, -6 * S),
                arrowprops=dict(arrowstyle="<->", color=VIOLET, lw=DIM_LW,
                                shrinkA=0, shrinkB=0))
    ax.plot([MAG_XS[0] * S, MAG_XS[0] * S], [0, -6 * S],
            color=VIOLET, lw=EXT_LW, alpha=0.5)
    ax.plot([MAG_XS[1] * S, MAG_XS[1] * S], [0, -6 * S],
            color=VIOLET, lw=EXT_LW, alpha=0.5)
    ax.text((MAG_XS[0] + MAG_XS[1]) / 2 * S, -7.5 * S,
            f"{MAG_XS[1] - MAG_XS[0]:.1f} typ.",
            fontsize=6.5, ha="center", va="top", color=VIOLET,
            fontfamily="sans-serif")

    # stacking rib inset from the left edge
    _dim_h(ax, STACK_YS[0] * S - STACK_W * S, 0, STACK_XS[0] * S,
           f"{STACK_INSET_X:.0f}", offset=-8 * S, side="below", fontsize=6.5)

    _title_block(ax, "Top Plan View", f"Scale {S}:1 (screen)")

    ax.autoscale_view()
    ax.margins(0.06)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", pad_inches=0.4,
                facecolor=BG)
    plt.close(fig)
    print("wrote", out_path)


# ---- technical drawing 2: front elevation (Y=0 face) ----
def _tech_front_elevation(out_path):
    S = 10.0
    fig, ax = plt.subplots(figsize=(16, 3.5), dpi=200)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # plate outline (front face: X vs Z, true scale)
    ax.add_patch(plt.Rectangle((0, 0), PLATE_X * S, PLATE_Z * S,
                 fc=SHAPE, alpha=0.08, ec=FG, lw=CUT_LW, zorder=3))

    # magnet bores (front face, true circles)
    for mx in MAG_XS:
        bore_cx = mx * S
        bore_cy = (PLATE_Z / 2) * S
        bore_r = (MAG_D / 2) * S
        ax.add_patch(plt.Circle((bore_cx, bore_cy), bore_r,
                     fc=VIOLET, alpha=0.15, ec=VIOLET, lw=0.8, zorder=4))
        ax.plot(bore_cx, bore_cy, "+", color=VIOLET, ms=4, mew=0.5, zorder=5)

    # overall X dimension (above)
    _dim_h(ax, PLATE_Z * S, 0, PLATE_X * S,
           f"{PLATE_X:.0f}", offset=6 * S)

    # overall Z dimension (right)
    _dim_v(ax, PLATE_X * S, 0, PLATE_Z * S,
           f"{PLATE_Z:.0f}", offset=8 * S)

    # magnet bore center height (left of first bore)
    _dim_v(ax, MAG_XS[0] * S, 0, (PLATE_Z / 2) * S,
           f"{PLATE_Z / 2:.1f}", offset=-6 * S, side="left", fontsize=6)

    _title_block(ax, "Front Elevation", f"Scale {S}:1 (screen)")

    ax.autoscale_view()
    ax.margins(x=0.03, y=0.15)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", pad_inches=0.3,
                facecolor=BG)
    plt.close(fig)
    print("wrote", out_path)


# ---- technical drawing 3: magnet-bore and stacking-joint detail ----
def _tech_detail(out_path):
    from matplotlib.patches import Polygon as MplPoly
    import matplotlib.gridspec as gridspec

    fig = plt.figure(figsize=(14, 6), dpi=200)
    fig.patch.set_facecolor(BG)
    gs = gridspec.GridSpec(1, 2, wspace=0.2)

    # ---- left: magnet bore detail (front/back face, Y-Z plane) ----
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_aspect("equal")
    ax1.axis("off")
    ax1.set_facecolor(BG)

    S1 = 45.0
    plate_y0_m = -2.0
    plate_y1_m = MAG_DEPTH + 8.0
    bore_r = MAG_D / 2
    mag_cz = PLATE_Z / 2

    plate_verts = [
        (plate_y0_m, 0), (plate_y1_m, 0),
        (plate_y1_m, PLATE_Z), (plate_y0_m, PLATE_Z),
    ]
    ax1.add_patch(MplPoly([(y * S1, z * S1) for y, z in plate_verts],
                  fc=SHAPE, alpha=0.10, ec=FG, lw=CUT_LW, zorder=2))
    _hatch_rect(ax1, plate_y0_m * S1, 0, plate_y1_m * S1,
                (mag_cz - bore_r) * S1, spacing=4.5)
    _hatch_rect(ax1, plate_y0_m * S1, (mag_cz + bore_r) * S1,
                plate_y1_m * S1, PLATE_Z * S1, spacing=4.5)
    _hatch_rect(ax1, MAG_DEPTH * S1, (mag_cz - bore_r) * S1,
                plate_y1_m * S1, (mag_cz + bore_r) * S1, spacing=4.5)

    bore_verts = [
        (0, mag_cz - bore_r), (MAG_DEPTH, mag_cz - bore_r),
        (MAG_DEPTH, mag_cz + bore_r), (0, mag_cz + bore_r),
    ]
    ax1.add_patch(MplPoly([(y * S1, z * S1) for y, z in bore_verts],
                  fc=BG, ec=FG, lw=CUT_LW, zorder=3))

    mag_r = 3.0
    mag_depth = 3.0
    mag_verts = [
        (0, mag_cz - mag_r), (mag_depth, mag_cz - mag_r),
        (mag_depth, mag_cz + mag_r), (0, mag_cz + mag_r),
    ]
    ax1.add_patch(MplPoly([(y * S1, z * S1) for y, z in mag_verts],
                  fc=VIOLET, alpha=0.2, ec=VIOLET, lw=0.8,
                  ls="--", zorder=4))
    ax1.text(mag_depth / 2 * S1, mag_cz * S1, "magnet\n6×3",
             fontsize=6.5, ha="center", va="center", color=VIOLET,
             fontfamily="sans-serif", fontstyle="italic", zorder=5)

    ax1.plot([0, 0], [-1 * S1, (PLATE_Z + 1) * S1],
             color=FG, lw=CUT_LW, zorder=3)
    ax1.plot([plate_y0_m * S1, plate_y1_m * S1],
             [mag_cz * S1, mag_cz * S1],
             color=DIM_COLOR, lw=0.4, ls=(0, (8, 4)), zorder=2)

    _dim_v(ax1, MAG_DEPTH / 2 * S1, (mag_cz - bore_r) * S1,
           (mag_cz + bore_r) * S1,
           f"⌀{MAG_D:.1f}", offset=5 * S1, fontsize=7)
    _dim_h(ax1, (mag_cz + bore_r) * S1, 0, MAG_DEPTH * S1,
           f"{MAG_DEPTH:.1f} deep", offset=3 * S1, fontsize=7)
    _dim_v(ax1, plate_y1_m * S1, 0, mag_cz * S1,
           f"{mag_cz:.1f}", offset=4 * S1, fontsize=6.5)
    _dim_v(ax1, plate_y1_m * S1, 0, PLATE_Z * S1,
           f"{PLATE_Z:.0f}", offset=9 * S1, fontsize=7)
    clearance = MAG_DEPTH - mag_depth
    if clearance > 0.05:
        _dim_h(ax1, (mag_cz - bore_r) * S1, mag_depth * S1, MAG_DEPTH * S1,
               f"{clearance:.1f}", offset=-3 * S1, side="below",
               fontsize=5.5)

    ax1.text(0.5, -0.02,
             f"Magnet Bore Detail  |  Scale {S1:.0f}:1",
             transform=ax1.transAxes, fontsize=7, ha="center", va="top",
             color=MUTED, fontfamily="sans-serif", fontweight="bold")

    # ---- right: stacking rib/groove joint detail (X-Z plane, one corner) ----
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_aspect("equal")
    ax2.axis("off")
    ax2.set_facecolor(BG)

    S2 = 22.0
    det_x0 = STACK_XS[0] - STACK_LEN / 2 - 4.0
    det_x1 = STACK_XS[0] + STACK_LEN / 2 + 4.0

    # this plate's body: bottom face carries the recessed groove, top face
    # carries the raised rib -- both are the same solid, shown together so
    # the joint is legible without drawing a second mating plate
    body_verts = [
        (det_x0, 0), (det_x1, 0), (det_x1, PLATE_Z), (det_x0, PLATE_Z),
    ]
    ax2.add_patch(MplPoly([(x * S2, z * S2) for x, z in body_verts],
                  fc=SHAPE, alpha=0.10, ec=FG, lw=CUT_LW, zorder=2))
    _hatch_rect(ax2, det_x0 * S2, 0, det_x1 * S2, PLATE_Z * S2, spacing=4.0)

    rib_x0 = STACK_XS[0] - STACK_LEN / 2
    rib_x1 = STACK_XS[0] + STACK_LEN / 2
    rib_verts = [
        (rib_x0, PLATE_Z), (rib_x1, PLATE_Z),
        (rib_x1, PLATE_Z + STACK_H), (rib_x0, PLATE_Z + STACK_H),
    ]
    ax2.add_patch(MplPoly([(x * S2, z * S2) for x, z in rib_verts],
                  fc=AMBER, alpha=0.55, ec=FG, lw=CUT_LW, zorder=4))

    play = STACK_PLAY / 2
    groove_verts = [
        (rib_x0 - play, 0), (rib_x1 + play, 0),
        (rib_x1 + play, STACK_H), (rib_x0 - play, STACK_H),
    ]
    ax2.add_patch(MplPoly([(x * S2, z * S2) for x, z in groove_verts],
                  fc=BG, ec=FG, lw=CUT_LW, zorder=4))

    ax2.text(STACK_XS[0] * S2, (PLATE_Z + STACK_H + 0.8) * S2,
             "rib (top face)", fontsize=6.5, ha="center", va="bottom",
             color=AMBER, fontfamily="sans-serif", fontstyle="italic",
             zorder=5)
    ax2.text(STACK_XS[0] * S2, (STACK_H / 2) * S2,
             "groove\n(bottom face)", fontsize=6, ha="center", va="center",
             color=MUTED, fontfamily="sans-serif", fontstyle="italic",
             zorder=5)

    _dim_v(ax2, rib_x1 * S2, PLATE_Z * S2, (PLATE_Z + STACK_H) * S2,
           f"{STACK_H:.1f}", offset=4 * S2, fontsize=7)
    _dim_h(ax2, PLATE_Z * S2, rib_x0 * S2, rib_x1 * S2,
           f"{STACK_LEN:.1f}", offset=-2.5 * S2, side="below", fontsize=6.5)
    _dim_v(ax2, (rib_x0 - play) * S2, 0, STACK_H * S2,
           f"{STACK_H:.1f} deep", offset=-4 * S2, side="left", fontsize=6.5)

    ax2.text(0.5, -0.02,
             f"Stacking Joint Detail  |  Scale {S2:.0f}:1",
             transform=ax2.transAxes, fontsize=7, ha="center", va="top",
             color=MUTED, fontfamily="sans-serif", fontweight="bold")

    _fit_view(ax1, ax2)

    fig.savefig(out_path, dpi=200, bbox_inches="tight", pad_inches=0.3,
                facecolor=BG)
    plt.close(fig)
    print("wrote", out_path)


_tech_top_plan(IMG_DIR / f"jig_plate_{VERSION}_tech_top.png")
_tech_front_elevation(IMG_DIR / f"jig_plate_{VERSION}_tech_front.png")
_tech_detail(IMG_DIR / f"jig_plate_{VERSION}_tech_detail.png")
