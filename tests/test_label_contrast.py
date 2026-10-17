"""Text contrast on all four drawings (jig-plate.py): every label must
reach the WCAG 1.4.3 minimum of 4.5:1 against what it sits on, which is BG
or a see-through tinted fill composited over BG.

The figures are captured by wrapping plt.close, which each drawing function
calls after saving.
"""
import importlib.util
from pathlib import Path

import pytest
from matplotlib.colors import to_rgba

from jig_plate_base import build_plate

_SCRIPT = Path(__file__).resolve().parent.parent / "jig-plate.py"
_spec = importlib.util.spec_from_file_location("jig_plate_cli_contrast", _SCRIPT)
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)

MIN_RATIO = 4.5


def _lum(rgb):
    def ch(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg, bg):
    a, b = sorted((_lum(fg), _lum(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _over(fg_rgba, bg_rgb):
    a = fg_rgba[3]
    return tuple(a * f + (1 - a) * b for f, b in zip(fg_rgba[:3], bg_rgb[:3]))


def _background(ax, text):
    """BG, or the topmost tinted patch under a data-space text, over BG."""
    bg = to_rgba(cli.BG)[:3]
    if text.get_transform() != ax.transData:
        return bg
    point = ax.transData.transform(text.get_position())
    under = []
    for p in ax.patches:
        if p.get_zorder() > text.get_zorder() or p.get_facecolor()[3] == 0:
            continue
        path = p.get_path().transformed(p.get_data_transform())
        if path.contains_point(point):
            under.append(p)
    for p in sorted(under, key=lambda p: p.get_zorder()):
        bg = _over(p.get_facecolor(), bg)
    return bg


@pytest.fixture(scope="module")
def figures(tmp_path_factory):
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
    assert len(captured) == 4
    return captured


def test_every_label_reaches_4_5_to_1(figures):
    failures = []
    checked = 0
    for fi, fig in enumerate(figures):
        axes = [a for ax in fig.axes for a in (ax, *ax.child_axes)]
        for ax in axes:
            for t in ax.texts:
                if not t.get_text().strip():
                    continue
                checked += 1
                fg = to_rgba(t.get_color())
                bg = _background(ax, t)
                r = ratio(_over(fg, bg), bg)
                if r < MIN_RATIO:
                    failures.append((fi, t.get_text(), t.get_color(), round(r, 2)))
    assert checked >= 30, checked
    assert not failures, failures


def test_text_palette_reaches_4_5_on_its_fills():
    bg = to_rgba(cli.BG)[:3]
    violet_tint = _over(cli._faint(cli.VIOLET, 0.2), bg)
    for name, color, back in (
            ("VIOLET_TEXT on tint", cli.VIOLET_TEXT, violet_tint),
            ("VIOLET_TEXT on BG", cli.VIOLET_TEXT, bg),
            ("AMBER_TEXT on BG", cli.AMBER_TEXT, bg),
            ("DIM_COLOR on BG", cli.DIM_COLOR, bg),
            ("MUTED on BG", cli.MUTED, bg),
            ("FG on BG", cli.FG, bg)):
        assert ratio(to_rgba(color)[:3], back) >= MIN_RATIO, name
