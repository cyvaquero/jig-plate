"""Jig plate -- CLI generator for the stackable laser-jig base plate.

VERSION below is the single source of truth: it drives the output
filenames and the 80-byte binary STL header of both meshes.

This is the base plate only -- no blank-specific pockets. Keeps only what is
blank-agnostic: the magnet bores and the corner stacking rib/groove system.
Pockets for a specific blank are added on top of this base in a separate
script.

The reusable geometry lives in jig_plate_base.py (a hyphenated filename
like this one can't itself be `import`ed). Other generator scripts should
`from jig_plate_base import build_plate` directly rather than running this
CLI; this script is the command-line entry point: argument parsing, STL
export, and the diagrams/technical drawings.

The debossed text label is parameterized via --label (default "Jig Plate");
the logo mark next to it is not. See build_plate()'s `label` parameter.

Changelog
  0.1.0  base design -- magnet bores and corner stacking rib/groove system,
         debossed "Jig Plate" wordmark, no pocket geometry
  1.0.0  first stable release -- script and documentation reviewed, no
         geometry changes; dead code removed from the stacking-joint
         detail drawing; documentation figure/filename inconsistencies
         corrected
  1.0.1  debossed text label parameterized via --label (default unchanged,
         "Jig Plate"); logo mark not parameterized -- a shift in how the
         plate is generated, so iterative bumps now also cover generation
         logic/parameters, not just default-output geometry
  1.0.2  debossed label font pinned to "DejaVu Sans" (matplotlib's bundled
         font) instead of the generic "sans-serif" family alias, so the
         debossed text is identical on macOS, Windows, and Linux instead
         of depending on the host's installed fonts; default output
         unchanged on this machine
  1.1.0  minor release folding 1.0.1-1.0.2
  1.1.1  plate geometry extracted into the importable jig_plate_base.py
         library (build_plate()); this script is now a thin CLI wrapper
         around it -- a shift in how the plate is generated, default
         output unchanged
  2.0.0  major release: two-file architecture becomes the project's public
         structure -- jig_plate_base.build_plate() is the supported API for
         other generator scripts to build on this base plate, jig-plate.py
         is CLI-only. Default output unchanged.
  2.0.1  default back_margin 17 -> 10 mm, matching the already-validated
         front_margin value; moves the back-corner mounting magnet bore
         and stacking rib/groove 3.5 mm closer to the back edge (bore-to-
         edge clearance 5.45 -> 1.95 mm, same clearance the front bore
         already has). Verified no collision with the stacking rib/groove
         (disjoint in X) and still watertight; volume/bbox unchanged.
  2.1.0  minor release folding 2.0.1
  2.1.1  corner stacking rib/groove reinset: stack_inset_x 6 -> 4 mm, and
         a new stack_inset_y (4 mm) decouples the rib/groove Y position
         from bottom_mag_ys, which it previously reused -- now a fixed
         4 mm inset from the corner on both axes, independent of the
         mounting-magnet border bands. Verified no collision with any
         magnet bore (all disjoint footprints) and still watertight;
         volume/bbox unchanged. Edge clearance in X drops 3 -> 1 mm.
  2.1.2  default bottom_mag_inset_x 20 -> 12 mm, bringing the bottom-face
         corner mounting magnets in toward the corner stacking rib/groove
         (the nearer feature -- their Y-bands already overlap, only X
         separated them). Gives a 1.95 mm wall between magnet bore and
         stacking rib/groove, the same clearance value already used
         elsewhere in this design. Verified no collision against any
         magnet bore or stack zone and still watertight; volume/bbox
         unchanged. The stack coupon already fully captures both features
         at this inset -- relabeled to reflect it now also validates this
         wall.
  2.1.3  stack_play now also opens up the groove's length (X), not just
         its width (Y) -- the rib/groove fit previously had zero
         clearance lengthwise while already having 0.2 mm of width play,
         an inconsistency rather than a deliberate tight fit. Groove is
         now 6.2 mm long (rib stays 6.0 mm). Magnet-to-groove wall drops
         1.95 -> 1.85 mm, groove edge clearance 1.0 -> 0.9 mm; both still
         comfortably positive. Verified still watertight; volume/bbox
         unchanged at display precision.
  2.2.0  minor release folding 2.1.1-2.1.3. Corner stacking coupon
         printed and physically test-stacked: fit confirmed good.
  2.2.1  debossed logo/label duplicated on the right face (x=plate_x),
         mirrored to read correctly from +X -- not a plain copy of the
         left-face cut: a viewer at -X (left face) has "right" = -Y,
         but a viewer at +X (right face) has "right" = +Y, so the
         local-x-to-Y mapping is unflipped here versus the left face's
         (verified by rendering each face's cut as its own viewer would
         see it: both read "Jig Plate" correctly, not mirrored/backwards).
         Verified still watertight; volume/bbox unchanged at display
         precision.
  2.3.0  minor release folding 2.2.1. Branding now duplicated on both
         side faces, each mirrored to read correctly from its own side.
  2.3.1  bottom-face honeycomb lightening cutout added to build_plate()
         (new honeycomb_enabled/honeycomb_skin/honeycomb_wall/
         honeycomb_af/honeycomb_margin_x/honeycomb_margin_y params,
         default honeycomb_enabled=True) -- a hex grid of blind pockets
         cut up from the bottom face, sized to match eu-business-card-jig's
         vented pocket floor (23.1 mm across flats, 2.6 mm walls), leaving
         a 2.4 mm top skin. Boundary cells are clipped via boolean
         intersection against the margin field and boolean difference
         against the bottom-corner mounting bores and corner stacking
         rib/groove footprints, rather than dropped whole. Default plate
         volume drops 481.5 -> 282.0 cm3 (-41.4%); top face, all magnet
         bores, and the stacking rib/groove/coupon are untouched. Verified
         still watertight.
  2.3.2  new --honeycomb-af CLI flag exposes build_plate()'s honeycomb_af
         parameter (cell size, mm across flats), default unchanged at
         23.1. Default plate output unaffected; verified still watertight
         at the default and at a sample override (--honeycomb-af 30).
  2.3.3  default honeycomb_af 23.1 -> 22.0 mm (across flats), and the
         --honeycomb-af CLI default follows. Default plate volume
         282.0 -> 285.5 cm3 (-41.4% -> -40.7% vs the solid baseline --
         smaller cells leave proportionally more wall material). Top
         face, all magnet bores, and the stacking rib/groove/coupon are
         untouched. Verified still watertight.
  2.4.0  minor release folding 2.3.1-2.3.3. Bottom-face honeycomb
         lightening cutout (22 mm cells across flats, 2.6 mm walls,
         boundary cells clipped rather than dropped) with cell size
         exposed via --honeycomb-af. Default plate volume
         481.5 -> 285.5 cm3 (-40.7%); top face, all magnet bores, and the
         stacking rib/groove/coupon are untouched. Verified still
         watertight.
  2.4.1  honeycomb_skin default reduced 2.4 -> 1.2 mm (3-perimeter
         minimum shell at a 0.4 mm nozzle) -- the honeycomb pockets
         already cut up to plate_z - honeycomb_skin, so this thins the
         solid top skin they stop at rather than changing what they cut
         up to. Default plate volume 285.5 -> 249.8 cm3 (-48.1% vs the
         solid baseline, up from -40.7%). Top face, all magnet bores, and
         the stacking rib/groove/coupon are untouched. Verified still
         watertight; the top face bridges an unsupported ~19 mm span over
         each honeycomb cell during printing (plate prints bottom-face-
         down per the README) and has not been physically validated for
         sag/warp at this thickness.
  2.4.2  new sparse-coffer bottom-face lightening cutout added to
         build_plate() as an alternative to the honeycomb (new
         coffer_enabled/coffer_skin/coffer_rib/coffer_cols/coffer_rows/
         coffer_margin_x/coffer_margin_y params, default
         coffer_enabled=False -- honeycomb stays the default), plus a new
         --lightening {honeycomb,coffer} CLI flag (default honeycomb) with
         --coffer-rib/--coffer-cols/--coffer-rows to tune it. Coffer is a
         cols x rows grid of large rectangular pockets (4x3 = 12 by
         default, 5 mm ribs) instead of the honeycomb's ~99 cells -- ~8x
         fewer islands to print for essentially the same material removal
         (254.5 cm3 / -47.2% vs the honeycomb's 249.8 cm3 / -48.1%),
         trading distributed bridge spans for fewer, wider ones. Default
         plate output unchanged; verified both paths still watertight.
  2.4.3  new --coffer-skin CLI flag (default 1.2, matching
         build_plate()'s coffer_skin default) for parity with the
         honeycomb path's skin control. Also: --honeycomb-af,
         --coffer-rib, --coffer-cols, --coffer-rows, and --coffer-skin
         now warn to stderr when passed opposite what --lightening
         selects (e.g. --coffer-rib with --lightening honeycomb, the
         default) instead of silently doing nothing -- the build still
         proceeds using only the selected pattern's options. Default
         plate output unaffected; verified still watertight at the
         default, with --coffer-skin overridden, and with each warning
         path triggered.
  2.4.4  new CLI flags expose the rest of build_plate()'s honeycomb
         parameters: --honeycomb-wall, --honeycomb-skin,
         --honeycomb-margin-x, --honeycomb-margin-y. --lightening gains a
         third choice, 'none', for a solid underside, folding in what a
         separately-developed --no-honeycomb flag would have done --
         --lightening is now the single switch across all three patterns
         rather than two overlapping toggles. All new-flag defaults
         unchanged. Also: unit tests added for jig_plate_base.build_plate()
         (32 tests, ~3s, via `pytest`) covering watertightness, volume/bbox
         regression, every honeycomb_*/coffer_* parameter across its
         range, and the CLAUDE.md design constraints. Default plate output
         unaffected; verified still watertight at the default, with
         --lightening none (481.5 cm3, matches the solid baseline), and
         with a combined override of every new flag.
  2.4.5  the honeycomb/coffer bottom-face lightening cutout (2.3.1-2.4.4)
         is scrapped -- material/print-time reduction will be handled in
         the slicer (infill) instead of the model. build_plate() and the
         CLI revert to their pre-2.3.1 state: no honeycomb_*/coffer_*
         parameters, no --lightening/--honeycomb-*/--coffer-* flags.
         Default plate volume 249.8 -> 481.5 cm3 (back to the solid
         slab); top face, all magnet bores, and the stacking
         rib/groove/coupon were already untouched by the removed cutout
         and remain so. Verified still watertight.
"""
import argparse
from pathlib import Path

import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from jig_plate_base import build_plate, bx

VERSION = "2.4.5"
OUT_DIR = Path(__file__).resolve().parent / "output"


# stamp the 80-byte binary STL header so the version travels with the file
def stamp(path, text):
    b = bytearray(open(path, "rb").read())
    b[0:80] = text.encode("ascii").ljust(80, b"\x00")
    open(path, "wb").write(b)


# -------- diagram / technical drawing styling --------
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
def _plate_diagram(out_path, geom):
    from matplotlib.patches import Polygon as MplPoly, Circle as MplCircle
    S = 1.8
    fig, ax = plt.subplots(figsize=(12, 8.5), dpi=200)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    px, py, pz = geom.plate_x * S, geom.plate_y * S, geom.plate_z * S * 3

    ax.add_patch(MplPoly(iso_rect(0, 0, px, py, pz),
                 fc=SHAPE, alpha=0.16, ec=FG, lw=0.5, zorder=2))
    ax.add_patch(MplPoly(iso_right_face(px, 0, py, 0, pz),
                 fc=SHAPE, alpha=0.42, ec=FG, lw=0.5, zorder=2))
    ax.add_patch(MplPoly(iso_front_face(0, px, py, 0, pz),
                 fc=SHAPE, alpha=0.30, ec=FG, lw=0.5, zorder=2))

    # magnet positions on the front edge, for reference
    for mx in geom.mag_xs:
        mag_pt = iso(mx * S, 0, pz * 0.5)
        ax.add_patch(MplCircle(mag_pt, 3.5, fc=VIOLET, alpha=0.6,
                     ec=FG, lw=0.4, zorder=4))

    # corner stacking rib footprint, top-left-front corner, for reference
    sx0, sy0 = geom.stack_xs[0] * S, geom.stack_ys[0] * S
    ax.add_patch(MplPoly(
        iso_rect(sx0 - geom.stack_len * S / 2, sy0 - geom.stack_w * S / 2,
                 sx0 + geom.stack_len * S / 2, sy0 + geom.stack_w * S / 2, pz),
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
           "Right edge (branding)", dashed=False)

    back_pt = iso(px * 0.25, py, pz * 0.35)
    leader(ax, back_pt, (back_pt[0] - 60, back_pt[1] - 60),
           "Back edge (magnets)", ha="right", dashed=False)

    bottom_pt = iso(px / 2, py, 0)
    leader(ax, bottom_pt, (bottom_pt[0] + 70, bottom_pt[1] - 30),
           "Bottom — sits on the bed, carries mounting magnets")

    mag_pt = iso(geom.mag_xs[1] * S, 0, pz * 0.5)
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
def _tech_top_plan(out_path, geom):
    S = 2.0
    fig, ax = plt.subplots(figsize=(14, 10), dpi=200)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # plate outline
    ax.add_patch(plt.Rectangle((0, 0), geom.plate_x * S, geom.plate_y * S,
                 fc="none", ec=FG, lw=CUT_LW, zorder=3))

    # magnet bores (front and back faces)
    for mx in geom.mag_xs:
        for y_face in [0, geom.plate_y]:
            ax.plot(mx * S, y_face * S, "o", color=VIOLET,
                    ms=geom.mag_d * S / 2, mfc="none", mew=1.0, zorder=5)
            ax.plot(mx * S, y_face * S, "+", color=VIOLET, ms=3, mew=0.6,
                    zorder=5)

    # bottom-face mounting magnets: hidden from this view (underside), so
    # drawn dashed per the hidden-line convention rather than the solid
    # circles used for the front/back through-faces above
    for mx in (geom.bottom_mag_inset_x, geom.plate_x - geom.bottom_mag_inset_x):
        for my in geom.bottom_mag_ys:
            ax.add_patch(plt.Circle((mx * S, my * S), geom.mag_d * S / 2,
                         fc="none", ec=VIOLET, lw=HIDDEN_LW, ls=HIDDEN_LS,
                         zorder=5))
            ax.plot(mx * S, my * S, "+", color=VIOLET, ms=3, mew=0.6,
                    zorder=5)

    # corner stacking ribs (top face, visible) / grooves (bottom, hidden
    # underneath at the same footprint plus play)
    for mx in geom.stack_xs:
        for my in geom.stack_ys:
            ax.add_patch(plt.Rectangle(
                (mx * S - geom.stack_len * S / 2, my * S - geom.stack_w * S / 2),
                geom.stack_len * S, geom.stack_w * S,
                fc=AMBER, alpha=0.6, ec=FG, lw=0.6, zorder=5))

    # overall dimensions
    _dim_h(ax, geom.plate_y * S, 0, geom.plate_x * S,
           f"{geom.plate_x:.0f}", offset=12 * S)
    _dim_v(ax, geom.plate_x * S, 0, geom.plate_y * S,
           f"{geom.plate_y:.0f}", offset=12 * S)

    # front border band (houses the bottom mounting magnet + branding)
    _dim_v(ax, 0, 0, geom.front_margin * S,
           f"{geom.front_margin:.0f}", offset=-15 * S, side="left")

    # magnet X positions
    ax.annotate("", xy=(geom.mag_xs[0] * S, -6 * S),
                xytext=(geom.mag_xs[1] * S, -6 * S),
                arrowprops=dict(arrowstyle="<->", color=VIOLET, lw=DIM_LW,
                                shrinkA=0, shrinkB=0))
    ax.plot([geom.mag_xs[0] * S, geom.mag_xs[0] * S], [0, -6 * S],
            color=VIOLET, lw=EXT_LW, alpha=0.5)
    ax.plot([geom.mag_xs[1] * S, geom.mag_xs[1] * S], [0, -6 * S],
            color=VIOLET, lw=EXT_LW, alpha=0.5)
    ax.text((geom.mag_xs[0] + geom.mag_xs[1]) / 2 * S, -7.5 * S,
            f"{geom.mag_xs[1] - geom.mag_xs[0]:.1f} typ.",
            fontsize=6.5, ha="center", va="top", color=VIOLET,
            fontfamily="sans-serif")

    # stacking rib inset from the left edge
    _dim_h(ax, geom.stack_ys[0] * S - geom.stack_w * S, 0, geom.stack_xs[0] * S,
           f"{geom.stack_inset_x:.0f}", offset=-8 * S, side="below",
           fontsize=6.5)

    _title_block(ax, "Top Plan View", f"Scale {S}:1 (screen)")

    ax.autoscale_view()
    ax.margins(0.06)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", pad_inches=0.4,
                facecolor=BG)
    plt.close(fig)
    print("wrote", out_path)


# ---- technical drawing 2: front elevation (Y=0 face) ----
def _tech_front_elevation(out_path, geom):
    S = 10.0
    fig, ax = plt.subplots(figsize=(16, 3.5), dpi=200)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # plate outline (front face: X vs Z, true scale)
    ax.add_patch(plt.Rectangle((0, 0), geom.plate_x * S, geom.plate_z * S,
                 fc=SHAPE, alpha=0.08, ec=FG, lw=CUT_LW, zorder=3))

    # magnet bores (front face, true circles)
    for mx in geom.mag_xs:
        bore_cx = mx * S
        bore_cy = (geom.plate_z / 2) * S
        bore_r = (geom.mag_d / 2) * S
        ax.add_patch(plt.Circle((bore_cx, bore_cy), bore_r,
                     fc=VIOLET, alpha=0.15, ec=VIOLET, lw=0.8, zorder=4))
        ax.plot(bore_cx, bore_cy, "+", color=VIOLET, ms=4, mew=0.5, zorder=5)

    # overall X dimension (above)
    _dim_h(ax, geom.plate_z * S, 0, geom.plate_x * S,
           f"{geom.plate_x:.0f}", offset=6 * S)

    # overall Z dimension (right)
    _dim_v(ax, geom.plate_x * S, 0, geom.plate_z * S,
           f"{geom.plate_z:.0f}", offset=8 * S)

    # magnet bore center height (left of first bore)
    _dim_v(ax, geom.mag_xs[0] * S, 0, (geom.plate_z / 2) * S,
           f"{geom.plate_z / 2:.1f}", offset=-6 * S, side="left", fontsize=6)

    _title_block(ax, "Front Elevation", f"Scale {S}:1 (screen)")

    ax.autoscale_view()
    ax.margins(x=0.03, y=0.15)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", pad_inches=0.3,
                facecolor=BG)
    plt.close(fig)
    print("wrote", out_path)


# ---- technical drawing 3: magnet-bore and stacking-joint detail ----
def _tech_detail(out_path, geom):
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
    plate_y1_m = geom.mag_depth + 8.0
    bore_r = geom.mag_d / 2
    mag_cz = geom.plate_z / 2

    plate_verts = [
        (plate_y0_m, 0), (plate_y1_m, 0),
        (plate_y1_m, geom.plate_z), (plate_y0_m, geom.plate_z),
    ]
    ax1.add_patch(MplPoly([(y * S1, z * S1) for y, z in plate_verts],
                  fc=SHAPE, alpha=0.10, ec=FG, lw=CUT_LW, zorder=2))
    _hatch_rect(ax1, plate_y0_m * S1, 0, plate_y1_m * S1,
                (mag_cz - bore_r) * S1, spacing=4.5)
    _hatch_rect(ax1, plate_y0_m * S1, (mag_cz + bore_r) * S1,
                plate_y1_m * S1, geom.plate_z * S1, spacing=4.5)
    _hatch_rect(ax1, geom.mag_depth * S1, (mag_cz - bore_r) * S1,
                plate_y1_m * S1, (mag_cz + bore_r) * S1, spacing=4.5)

    bore_verts = [
        (0, mag_cz - bore_r), (geom.mag_depth, mag_cz - bore_r),
        (geom.mag_depth, mag_cz + bore_r), (0, mag_cz + bore_r),
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

    ax1.plot([0, 0], [-1 * S1, (geom.plate_z + 1) * S1],
             color=FG, lw=CUT_LW, zorder=3)
    ax1.plot([plate_y0_m * S1, plate_y1_m * S1],
             [mag_cz * S1, mag_cz * S1],
             color=DIM_COLOR, lw=0.4, ls=(0, (8, 4)), zorder=2)

    _dim_v(ax1, geom.mag_depth / 2 * S1, (mag_cz - bore_r) * S1,
           (mag_cz + bore_r) * S1,
           f"⌀{geom.mag_d:.1f}", offset=5 * S1, fontsize=7)
    _dim_h(ax1, (mag_cz + bore_r) * S1, 0, geom.mag_depth * S1,
           f"{geom.mag_depth:.1f} deep", offset=3 * S1, fontsize=7)
    _dim_v(ax1, plate_y1_m * S1, 0, mag_cz * S1,
           f"{mag_cz:.1f}", offset=4 * S1, fontsize=6.5)
    _dim_v(ax1, plate_y1_m * S1, 0, geom.plate_z * S1,
           f"{geom.plate_z:.0f}", offset=9 * S1, fontsize=7)
    clearance = geom.mag_depth - mag_depth
    if clearance > 0.05:
        _dim_h(ax1, (mag_cz - bore_r) * S1, mag_depth * S1, geom.mag_depth * S1,
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
    det_x0 = geom.stack_xs[0] - geom.stack_len / 2 - 4.0
    det_x1 = geom.stack_xs[0] + geom.stack_len / 2 + 4.0

    # this plate's body: bottom face carries the recessed groove, top face
    # carries the raised rib -- both are the same solid, shown together so
    # the joint is legible without drawing a second mating plate
    body_verts = [
        (det_x0, 0), (det_x1, 0), (det_x1, geom.plate_z), (det_x0, geom.plate_z),
    ]
    ax2.add_patch(MplPoly([(x * S2, z * S2) for x, z in body_verts],
                  fc=SHAPE, alpha=0.10, ec=FG, lw=CUT_LW, zorder=2))
    _hatch_rect(ax2, det_x0 * S2, 0, det_x1 * S2, geom.plate_z * S2,
                spacing=4.0)

    rib_x0 = geom.stack_xs[0] - geom.stack_len / 2
    rib_x1 = geom.stack_xs[0] + geom.stack_len / 2
    rib_verts = [
        (rib_x0, geom.plate_z), (rib_x1, geom.plate_z),
        (rib_x1, geom.plate_z + geom.stack_h), (rib_x0, geom.plate_z + geom.stack_h),
    ]
    ax2.add_patch(MplPoly([(x * S2, z * S2) for x, z in rib_verts],
                  fc=AMBER, alpha=0.55, ec=FG, lw=CUT_LW, zorder=4))

    play = geom.stack_play / 2
    groove_verts = [
        (rib_x0 - play, 0), (rib_x1 + play, 0),
        (rib_x1 + play, geom.stack_h), (rib_x0 - play, geom.stack_h),
    ]
    ax2.add_patch(MplPoly([(x * S2, z * S2) for x, z in groove_verts],
                  fc=BG, ec=FG, lw=CUT_LW, zorder=4))

    ax2.text(geom.stack_xs[0] * S2, (geom.plate_z + geom.stack_h + 0.8) * S2,
             "rib (top face)", fontsize=6.5, ha="center", va="bottom",
             color=AMBER, fontfamily="sans-serif", fontstyle="italic",
             zorder=5)
    ax2.text(geom.stack_xs[0] * S2, (geom.stack_h / 2) * S2,
             "groove\n(bottom face)", fontsize=6, ha="center", va="center",
             color=MUTED, fontfamily="sans-serif", fontstyle="italic",
             zorder=5)

    _dim_v(ax2, rib_x1 * S2, geom.plate_z * S2, (geom.plate_z + geom.stack_h) * S2,
           f"{geom.stack_h:.1f}", offset=4 * S2, fontsize=7)
    _dim_h(ax2, geom.plate_z * S2, rib_x0 * S2, rib_x1 * S2,
           f"{geom.stack_len:.1f}", offset=-2.5 * S2, side="below",
           fontsize=6.5)
    _dim_v(ax2, (rib_x0 - play) * S2, 0, geom.stack_h * S2,
           f"{geom.stack_h:.1f} deep", offset=-4 * S2, side="left",
           fontsize=6.5)

    ax2.text(0.5, -0.02,
             f"Stacking Joint Detail  |  Scale {S2:.0f}:1",
             transform=ax2.transAxes, fontsize=7, ha="center", va="top",
             color=MUTED, fontfamily="sans-serif", fontweight="bold")

    _fit_view(ax1, ax2)

    fig.savefig(out_path, dpi=200, bbox_inches="tight", pad_inches=0.3,
                facecolor=BG)
    plt.close(fig)
    print("wrote", out_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate the jig plate base STL, diagram, and "
                     "technical drawings."
    )
    parser.add_argument(
        "--label", default="Jig Plate",
        help='Text debossed on the top and left faces, next to the logo '
             'mark (the logo itself is not parameterized). '
             'Default: "Jig Plate".',
    )
    args = parser.parse_args()

    result = build_plate(label=args.label)
    solid = result.solid
    geom = result.geometry

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

    OUT_DIR.mkdir(exist_ok=True)
    OUT = OUT_DIR / f"jig_plate_{VERSION}.stl"
    solid.export(OUT)
    print("wrote", OUT)
    stamp(
        OUT,
        f"Jig plate {VERSION} | "
        f"{geom.plate_x:.0f}x{geom.plate_y:.0f}x{geom.plate_z:.0f}mm | "
        f"base plate, no pockets",
    )

    # test coupon: front-right corner, carrying the stacking rib/groove and
    # its bottom mounting magnet -- for validating the corner stacking fit
    # AND the wall between the magnet bore and the stacking rib/groove
    # (1.95 mm at the defaults), independently of any pocket layout added
    # later. Print two to mate. The cut region (46 x 20 mm) is sized to
    # fully contain both features at the default stack_inset_x/_y and
    # bottom_mag_inset_x -- if either moves much closer to this corner,
    # re-check that both stay fully inside SC_X0/SC_Y1 below.
    STACK_COUPON = OUT_DIR / f"jig_plate_{VERSION}_stack_coupon.stl"
    SC_X0, SC_Y0, SC_Y1 = geom.plate_x - 46.0, 0.0, 20.0
    stack_coupon = trimesh.boolean.intersection(
        [solid, bx(SC_X0, SC_Y0, -1, geom.plate_x, SC_Y1, geom.plate_z + geom.stack_h + 1)],
        engine="manifold",
    )
    stack_coupon.export(STACK_COUPON)
    print("wrote", STACK_COUPON)
    stamp(
        STACK_COUPON,
        f"Jig plate {VERSION} | "
        f"stack coupon {geom.plate_x - SC_X0:g}x{SC_Y1 - SC_Y0:g}"
        f"x{geom.plate_z:.0f}mm | corner, magnet+rib wall test",
    )
    print(
        "stack coupon:",
        stack_coupon.is_watertight,
        round(stack_coupon.volume / 1000, 2),
        "cm3",
        np.round(stack_coupon.bounds[1] - stack_coupon.bounds[0], 2),
    )

    IMG_DIR = Path(__file__).resolve().parent / "images"
    IMG_DIR.mkdir(exist_ok=True)
    _plate_diagram(IMG_DIR / f"jig_plate_{VERSION}_diagram.png", geom)
    _tech_top_plan(IMG_DIR / f"jig_plate_{VERSION}_tech_top.png", geom)
    _tech_front_elevation(IMG_DIR / f"jig_plate_{VERSION}_tech_front.png", geom)
    _tech_detail(IMG_DIR / f"jig_plate_{VERSION}_tech_detail.png", geom)


if __name__ == "__main__":
    main()
