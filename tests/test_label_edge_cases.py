"""Label-cutter edge cases the default glyphs never produce.

DejaVu Sans glyphs (checked U+0020..U+024F) never yield an invalid polygon
or a sub-0.01 mm2 piece, so these drive the helpers directly with input
the font cannot supply: a self-intersecting outline, and empty or tiny
polygons in the cutter input.
"""
import numpy as np
import pytest
from matplotlib.path import Path
from matplotlib.textpath import text_to_path
from shapely.geometry import MultiPolygon, Polygon

import jig_plate_base as base


def _square(side):
    return Polygon([(0, 0), (side, 0), (side, side), (0, side)])


def test_self_intersecting_outline_is_repaired_not_dropped(monkeypatch):
    # a bowtie: Polygon() on it is invalid and its signed area is 0, so
    # without the buffer(0) repair it would be filtered out as empty
    bowtie = np.array([(0, 0), (10, 10), (10, 0), (0, 10), (0, 0)], float)
    codes = [Path.MOVETO, Path.LINETO, Path.LINETO, Path.LINETO,
             Path.CLOSEPOLY]
    monkeypatch.setattr(
        text_to_path, "get_text_path",
        lambda *a, **k: (bowtie, codes),
    )
    size = text_to_path.FONT_SCALE  # 1:1 scale
    polys = base._text_polys("x", size, 0, 0)
    assert polys and all(p.is_valid for p in polys)
    # buffer(0) keeps at least one of the two 25 mm2 triangles (which
    # lobes survive is GEOS's choice, so don't pin the exact total)
    assert sum(p.area for p in polys) >= 25.0 - 1e-6


@pytest.mark.parametrize("cutter, args", [
    (base._add_deboss, (9.0, 0.3)),
    (base._add_deboss_left, (218.0, 0.3)),
    (base._add_deboss_right, (246.0, 218.0, 0.3)),
])
def test_cutter_skips_empty_and_sub_threshold_pieces(cutter, args):
    tiny = _square(0.05)  # 0.0025 mm2, under the 0.01 mm2 floor
    multi = MultiPolygon([_square(1.0).buffer(0), Polygon(
        [(5, 5), (5.05, 5), (5.05, 5.05), (5, 5.05)])])
    target = []
    cutter([Polygon(), tiny, _square(1.0), multi], target, *args)
    # the 1 mm square, and the 1 mm square inside the multipolygon
    assert len(target) == 2
    assert all(m.volume == pytest.approx(0.5) for m in target)
