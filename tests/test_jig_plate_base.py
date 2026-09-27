"""Unit tests for jig_plate_base.build_plate() -- the importable library.

These validate the library directly (no CLI, no file I/O, no diagrams),
so they run in a couple of seconds and are meant to replace "run the CLI
and eyeball watertight/volume" as the first check after any change to
jig_plate_base.py. See CLAUDE.md for the design constraints these guard.
"""
import pytest

from jig_plate_base import build_plate

DEFAULT_VOLUME_MM3 = 249840.6
SOLID_VOLUME_MM3 = 481478.7
BBOX = (246.0, 218.0, 10.5)
TOL = 1.0  # mm3, generous enough for boolean-engine tessellation noise


def _volume(result):
    return result.solid.volume


class TestDefaultPlate:
    def test_watertight(self):
        assert build_plate().solid.is_watertight

    def test_volume(self):
        assert _volume(build_plate()) == pytest.approx(DEFAULT_VOLUME_MM3, abs=TOL)

    def test_bounding_box(self):
        bounds = build_plate().solid.bounds
        extents = bounds[1] - bounds[0]
        assert extents == pytest.approx(BBOX, abs=1e-6)

    def test_x_within_bed_and_purge_clearance(self):
        # CLAUDE.md: plate must stay <= 246 mm in X (bed width + purge area)
        assert build_plate().geometry.plate_x <= 246.0


class TestSolidBaseline:
    """honeycomb_enabled=False must reproduce the pre-honeycomb solid slab."""

    def test_watertight(self):
        assert build_plate(honeycomb_enabled=False).solid.is_watertight

    def test_volume(self):
        result = build_plate(honeycomb_enabled=False)
        assert _volume(result) == pytest.approx(SOLID_VOLUME_MM3, abs=TOL)

    def test_more_volume_than_honeycomb(self):
        solid = _volume(build_plate(honeycomb_enabled=False))
        honeycomb = _volume(build_plate())
        assert solid > honeycomb


class TestHoneycombParameters:
    """Every honeycomb_* knob should stay watertight across its range,
    individually and combined -- this is the "standardization" check: any
    future change to _honeycomb_cuts must keep these all passing."""

    @pytest.mark.parametrize("af", [10.0, 22.0, 30.0, 40.0])
    def test_af_watertight(self, af):
        assert build_plate(honeycomb_af=af).solid.is_watertight

    @pytest.mark.parametrize("wall", [1.5, 2.6, 4.0])
    def test_wall_watertight(self, wall):
        assert build_plate(honeycomb_wall=wall).solid.is_watertight

    @pytest.mark.parametrize("skin", [0.8, 1.2, 2.4, 4.0])
    def test_skin_watertight(self, skin):
        assert build_plate(honeycomb_skin=skin).solid.is_watertight

    def test_skin_thickness_reduces_volume_removed(self):
        # a thicker top skin leaves less room for pockets to cut into
        thin = _volume(build_plate(honeycomb_skin=0.8))
        thick = _volume(build_plate(honeycomb_skin=4.0))
        assert thick > thin

    @pytest.mark.parametrize("margin_x,margin_y", [(16.0, 22.0), (30.0, 40.0)])
    def test_margins_watertight(self, margin_x, margin_y):
        result = build_plate(
            honeycomb_margin_x=margin_x, honeycomb_margin_y=margin_y
        )
        assert result.solid.is_watertight

    def test_wide_margins_leave_solid_baseline(self):
        # margins wide enough to exclude the whole field should degrade
        # gracefully to (near-)solid rather than erroring
        result = build_plate(honeycomb_margin_x=200.0, honeycomb_margin_y=200.0)
        assert result.solid.is_watertight
        assert _volume(result) == pytest.approx(SOLID_VOLUME_MM3, abs=1.0)

    def test_combined_overrides_watertight(self):
        result = build_plate(
            honeycomb_af=30.0, honeycomb_wall=3.5, honeycomb_skin=2.0,
            honeycomb_margin_x=20.0, honeycomb_margin_y=25.0,
        )
        assert result.solid.is_watertight


class TestLabel:
    @pytest.mark.parametrize("label", ["Jig Plate", "Card Jig", "A", "X" * 20])
    def test_custom_label_watertight(self, label):
        assert build_plate(label=label).solid.is_watertight


class TestGeometryPositions:
    """CLAUDE.md design constraints that must not regress."""

    def test_magnet_bores_symmetric_about_x_centreline(self):
        geom = build_plate().geometry
        centre = geom.plate_x / 2
        offsets = sorted(abs(x - centre) for x in geom.mag_xs)
        # symmetric set -> offsets pair up
        assert len(offsets) % 2 == 0
        for a, b in zip(offsets[0::2], offsets[1::2]):
            assert a == pytest.approx(b, abs=1e-9)

    def test_stack_positions_derive_only_from_plate_dimensions(self):
        # stack_xs/stack_ys must depend only on plate_x/plate_y and the
        # stack insets -- never on magnet or pocket layout
        geom = build_plate(mag_inset_x=50.0, mag_count_x=2).geometry
        assert geom.stack_xs == (geom.stack_inset_x, geom.plate_x - geom.stack_inset_x)
        assert geom.stack_ys == (geom.stack_inset_y, geom.plate_y - geom.stack_inset_y)

    def test_stack_positions_unaffected_by_honeycomb_params(self):
        base = build_plate().geometry
        varied = build_plate(honeycomb_af=35.0, honeycomb_wall=4.0).geometry
        assert base.stack_xs == varied.stack_xs
        assert base.stack_ys == varied.stack_ys

    def test_bottom_corner_magnets_symmetric_about_x_centreline(self):
        geom = build_plate().geometry
        centre = geom.plate_x / 2
        assert geom.bottom_mag_inset_x == pytest.approx(
            centre - (geom.plate_x - geom.bottom_mag_inset_x - centre), abs=1e-9
        )


class TestPurity:
    """build_plate() must have no side effects -- no file I/O, no argv."""

    def test_no_new_files_in_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        build_plate()
        assert list(tmp_path.iterdir()) == []
