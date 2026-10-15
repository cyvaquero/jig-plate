"""Layout checks on the isometric overview diagram (jig-plate.py).

The figure is captured by wrapping plt.close, which _plate_diagram calls
after saving, so the artists can be inspected without parsing the PNG.
"""
import importlib.util
from pathlib import Path

import pytest

from jig_plate_base import build_plate

_SCRIPT = Path(__file__).resolve().parent.parent / "jig-plate.py"
_spec = importlib.util.spec_from_file_location("jig_plate_cli_diagram", _SCRIPT)
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)


@pytest.fixture(scope="module")
def iso_axes(tmp_path_factory):
    captured = []
    real_close = cli.plt.close
    cli.plt.close = lambda fig=None: (captured.append(fig), real_close(fig))
    try:
        cli._plate_diagram(tmp_path_factory.mktemp("img") / "d.png",
                           build_plate().geometry)
    finally:
        cli.plt.close = real_close
    fig = captured[0]
    yield fig.axes[0]


def _leaders(ax):
    """Map label text -> (anchor, text_pos) segment of its leader line."""
    segs = {}
    for text in ax.texts:
        pos = tuple(text.get_position())
        for line in ax.lines:
            xs, ys = line.get_xdata(), line.get_ydata()
            if len(xs) == 2 and (xs[1], ys[1]) == pos:
                segs[text.get_text()] = ((xs[0], ys[0]), pos)
    return segs


def _ccw(a, b, c):
    return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])


def _intersect(s1, s2):
    (a, b), (c, d) = s1, s2
    return (_ccw(a, c, d) * _ccw(b, c, d) < 0) and (_ccw(a, b, c) * _ccw(a, b, d) < 0)


def test_every_callout_has_a_leader(iso_axes):
    assert len(_leaders(iso_axes)) == 5


def test_no_two_leaders_cross(iso_axes):
    segs = list(_leaders(iso_axes).items())
    crossings = [(a, b) for i, (a, sa) in enumerate(segs)
                 for b, sb in segs[i + 1:] if _intersect(sa, sb)]
    assert crossings == []
