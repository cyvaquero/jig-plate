"""Checks on the isometric diagram's corner-rib inset (jig-plate.py).

The figure is captured by wrapping plt.close, which _plate_diagram calls
after saving, so the artists can be inspected without parsing the PNG.
"""
import importlib.util
from pathlib import Path

import pytest

from jig_plate_base import build_plate

_SCRIPT = Path(__file__).resolve().parent.parent / "jig-plate.py"
_spec = importlib.util.spec_from_file_location("jig_plate_cli_inset", _SCRIPT)
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)


@pytest.fixture(scope="module")
def iso_axes(tmp_path_factory):
    captured = []
    real_close = cli.plt.close
    # keep the figure open (and its Agg canvas) so it can be measured
    cli.plt.close = lambda fig=None: captured.append(fig)
    try:
        cli._plate_diagram(tmp_path_factory.mktemp("img") / "d.png",
                           build_plate().geometry)
    finally:
        cli.plt.close = real_close
    fig = captured[0]
    fig.canvas.draw()
    yield fig.axes[0]
    real_close(fig)


def test_corner_rib_inset_is_present_and_labeled_with_its_scale(iso_axes):
    fig = iso_axes.figure
    assert len(iso_axes.child_axes) == 1
    inset = iso_axes.child_axes[0]
    titles = [t.get_text() for t in inset.texts]
    assert any(f"×{cli.INSET_ZOOM}" in t and "Detail A" in t for t in titles)
    assert any(t == "rib" for t in [a.get_text() for a in inset.texts])


def _amber_top(axes, alpha):
    want = tuple(cli._faint(cli.AMBER, alpha))
    (patch,) = [p for p in axes.patches
               if type(p).__name__ == "Polygon" and tuple(p.get_fc()) == want]
    return patch


def test_corner_rib_inset_magnification_matches_its_label(iso_axes):
    # the rib's top face, measured in rendered pixels in the inset and in
    # the main view, must differ by exactly the labeled zoom
    main = _amber_top(iso_axes, 0.7).get_window_extent()
    inset = _amber_top(iso_axes.child_axes[0], 0.9).get_window_extent()
    assert inset.width / main.width == pytest.approx(cli.INSET_ZOOM, rel=0.01)
    assert inset.height / main.height == pytest.approx(cli.INSET_ZOOM, rel=0.01)


def test_corner_rib_inset_clears_the_plate_and_every_label(iso_axes):
    from matplotlib.patches import Polygon
    fig = iso_axes.figure
    renderer = fig.canvas.get_renderer()
    inset_box = iso_axes.child_axes[0].get_window_extent()
    for text in iso_axes.texts:
        assert not text.get_window_extent(renderer).overlaps(inset_box), text.get_text()
    for patch in iso_axes.patches:
        if isinstance(patch, Polygon) and patch.get_fc()[3] > 0:
            path = patch.get_transform().transform_path(patch.get_path())
            assert not path.intersects_bbox(inset_box, filled=True)
