"""Legibility rules for the four drawings and their README presentation
(jig-plate.py, README.md): label size floor, front-elevation size, key
swatch and extension-line contrast, the small-span rib-inset dimension,
and linked README images.

Figures are captured by wrapping plt.close, which each drawing function
calls after saving.
"""
import importlib.util
import re
from pathlib import Path

import pytest
from matplotlib.colors import to_rgba
from matplotlib.patches import FancyBboxPatch
from matplotlib.text import Annotation

from jig_plate_base import build_plate

_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "jig_plate_cli_legibility", _ROOT / "jig-plate.py")
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)

NAMES = ("diagram", "top", "front", "detail")


def _lum(rgb):
    def ch(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(a, b):
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.fixture(scope="module")
def figs(tmp_path_factory):
    captured = []
    real_close = cli.plt.close
    cli.plt.close = lambda fig=None: (captured.append(fig), real_close(fig))
    out = tmp_path_factory.mktemp("img")
    geom = build_plate().geometry
    try:
        cli._plate_diagram(out / "d.png", geom)
        cli._tech_top_plan(out / "t.png", geom)
        cli._tech_front_elevation(out / "f.png", geom)
        cli._tech_detail(out / "x.png", geom)
    finally:
        cli.plt.close = real_close
    return dict(zip(NAMES, captured))


def _axes(fig):
    return [a for ax in fig.axes for a in (ax, *ax.child_axes)]


def test_no_label_is_smaller_than_7_pt(figs):
    small = []
    for name, fig in figs.items():
        for ax in _axes(fig):
            for t in ax.texts:
                if t.get_text().strip() and t.get_fontsize() < 7:
                    small.append((name, t.get_text(), t.get_fontsize()))
    assert not small, small


def test_front_elevation_figure_is_narrower_than_before(figs):
    # 16 x 3.5 in made its labels the smallest at README width
    w, h = figs["front"].get_size_inches()
    assert w < 16 and h < 3.5


def test_key_swatches_are_outlined_and_reach_3_to_1(figs):
    swatches = [p for p in figs["diagram"].axes[0].patches
                if isinstance(p, FancyBboxPatch)]
    assert len(swatches) == 3
    bg = to_rgba(cli.BG)
    for p in swatches:
        assert p.get_alpha() is None
        edge = p.get_edgecolor()
        assert edge[3] == 1.0
        assert _ratio(edge, bg) >= 3.0


def test_top_plan_violet_extension_lines_are_opaque_and_3_to_1(figs):
    ax = figs["top"].axes[0]
    ext = [ln for ln in ax.lines
           if ln.get_color() == cli.VIOLET and ln.get_linewidth() == cli.EXT_LW]
    assert len(ext) == 2
    for ln in ext:
        assert ln.get_alpha() in (None, 1.0)
    assert _ratio(to_rgba(cli.VIOLET), to_rgba(cli.BG)) >= 3.0


def test_rib_inset_dimension_uses_outside_arrows(figs):
    """The 4 mm span is narrower than two arrowheads; its label is an
    offset annotation (outside style), not a plain text on the line."""
    ax = figs["top"].axes[0]
    four = [t for t in ax.texts if t.get_text() == "4"]
    assert len(four) == 1
    assert isinstance(four[0], Annotation)


def test_readme_images_link_to_their_full_size_file():
    readme = (_ROOT / "README.md").read_text()
    images = re.findall(r"!\[[^\]]*\]\((docs/images/[a-z_]+\.png)\)", readme)
    assert len(images) == 4
    for path in images:
        assert f"]({path})]({path})" in readme, path


def test_readme_tables_have_real_headers():
    readme = (_ROOT / "README.md").read_text()
    assert "| | |" not in readme


def test_bore_height_label_clears_the_plate_outline(figs):
    """The 4.5 label sits outside the plate (left of x = 0), so it touches
    no outline; at 7 pt it did not fit between the bottom edge and the
    bore line inside the plate."""
    fig = figs["front"]
    ax = fig.axes[0]
    fig.canvas.draw()
    label = next(t for t in ax.texts if t.get_text() == "4.5")
    box = label.get_window_extent(fig.canvas.get_renderer())
    plate_x0 = ax.transData.transform((0, 0))[0]
    assert box.x1 < plate_x0
