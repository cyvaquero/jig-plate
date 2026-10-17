"""The top plan and front elevation each carry a key naming every line
style that distinguishes a feature (jig-plate.py), so hidden grooves, hidden
bores and ribs can be told apart without color.

The figures are captured by wrapping plt.close, which each drawing calls
after saving.
"""
import importlib.util
from pathlib import Path

import pytest

from jig_plate_base import build_plate

_SCRIPT = Path(__file__).resolve().parent.parent / "jig-plate.py"
_spec = importlib.util.spec_from_file_location("jig_plate_cli_key", _SCRIPT)
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)


def _capture(fn, tmp_path):
    captured = []
    real_close = cli.plt.close
    cli.plt.close = lambda fig=None: (captured.append(fig), real_close(fig))
    try:
        fn(tmp_path / "x.png", build_plate().geometry)
    finally:
        cli.plt.close = real_close
    return captured[0].axes[0]


EXPECTED = {
    "top": ["dashed rectangle: stacking groove (hidden, bottom face)",
            "dashed circle: mounting magnet bore (hidden, bottom face)",
            "dashed rectangle at the edge: magnet bore (hidden, front and back faces)",
            "solid filled rectangle: stacking rib (top face)"],
    "front": ["solid circle: magnet bore (front face)",
              "dashed rectangle: mounting magnet bore (hidden, bottom face)",
              "dashed rectangle: stacking groove (hidden, bottom face)",
              "solid filled rectangle: stacking rib (top face)"],
}


@pytest.mark.parametrize("name,fn", [
    ("top", "_tech_top_plan"), ("front", "_tech_front_elevation")])
def test_sheet_has_feature_key(tmp_path, name, fn):
    ax = _capture(getattr(cli, fn), tmp_path)
    texts = [t.get_text() for t in ax.texts]
    for entry in EXPECTED[name]:
        assert entry in texts, entry


@pytest.mark.parametrize("name,fn", [
    ("top", "_tech_top_plan"), ("front", "_tech_front_elevation")])
def test_key_swatches_use_the_feature_line_style(tmp_path, name, fn):
    """Each 'dashed' entry has a dashed swatch and each 'solid' one a solid
    swatch, so the key does not rely on color."""
    ax = _capture(getattr(cli, fn), tmp_path)
    key_patches = [p for p in ax.patches if not p.get_clip_on()]
    assert len(key_patches) == 4
    for patch, label in zip(key_patches, EXPECTED[name]):
        dashed = patch.get_linestyle() not in ("-", "solid")
        assert dashed == label.startswith("dashed"), label
