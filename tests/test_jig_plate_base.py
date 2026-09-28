"""Unit tests for jig_plate_base.build_plate() -- the importable library.

These validate the library directly (no CLI, no file I/O, no diagrams),
so they run in a couple of seconds and are meant to replace "run the CLI
and eyeball watertight/volume" as the first check after any change to
jig_plate_base.py. See CLAUDE.md for the design constraints these guard.

Geometry tests use `Trimesh.contains()` (ray/winding-number test) to
check actual cavities and solid material on the mesh, not just the
`PlateGeometry` record of where those features are supposed to be --
that record is pure passthrough of the input in several fields, so
comparing it against itself proves nothing about the generated solid.
"""
import numpy as np
import pytest

from jig_plate_base import build_plate

DEFAULT_VOLUME_MM3 = 481483.0
BBOX = (246.0, 218.0, 10.5)
TOL = 1.0  # mm3, generous enough for boolean-engine tessellation noise


def _volume(result):
    return result.solid.volume


def _cavity_center_x(solid, y, z, near_x):
    """X centre of the cavity bracketing `near_x`, measured on the mesh
    by ray-casting along +X at a fixed (y, z) and finding the pair of
    solid/cavity crossings nearest `near_x`. Precise (not a radius-wide
    contains() probe), so a several-mm shift in the real cut is caught
    even though a naive centre-point probe would still land inside it."""
    origin = [[-1.0, y, z]]
    direction = [[1.0, 0.0, 0.0]]
    locs, _, _ = solid.ray.intersects_location(origin, direction)
    xs = sorted(locs[:, 0])
    for i in range(len(xs) - 1):
        if xs[i] <= near_x <= xs[i + 1]:
            return (xs[i] + xs[i + 1]) / 2
    raise AssertionError(f"no cavity bracketing x={near_x}")


class TestDefaultPlate:
    def test_watertight(self):
        assert build_plate().solid.is_watertight

    def test_volume(self):
        assert _volume(build_plate()) == pytest.approx(DEFAULT_VOLUME_MM3, abs=TOL)

    def test_bounding_box(self):
        # also the CLAUDE.md constraint that plate_x <= 246 mm (bed width
        # + purge-area clearance): checked here against the actual mesh
        # bounding box, not just the plate_x argument passed back unchanged.
        bounds = build_plate().solid.bounds
        extents = bounds[1] - bounds[0]
        assert extents == pytest.approx(BBOX, abs=1e-6)
        assert extents[0] <= 246.0


class TestLabel:
    def test_empty_label_rejected(self):
        with pytest.raises(ValueError):
            build_plate(label="")

    def test_whitespace_only_label_rejected(self):
        with pytest.raises(ValueError):
            build_plate(label="   ")

    @pytest.mark.parametrize("label", ["Jig Plate", "Card Jig", "A", "X" * 20])
    def test_custom_label_watertight(self, label):
        assert build_plate(label=label).solid.is_watertight


class TestMeshGeometry:
    """Verify actual cavities/solid material on the generated mesh, not
    just the PlateGeometry record of where they're supposed to be."""

    def test_front_back_magnet_bores_are_cavities(self):
        result = build_plate()
        g, solid = result.geometry, result.solid
        z = g.plate_z / 2
        front_pts = [(mx, 0.5, z) for mx in g.mag_xs]
        back_pts = [(mx, g.plate_y - 0.5, z) for mx in g.mag_xs]
        assert not any(solid.contains(front_pts))
        assert not any(solid.contains(back_pts))

    def test_front_back_magnet_bores_share_x_position_on_the_mesh(self):
        # CLAUDE.md: "front and back bores share X positions ... so
        # plates mate either way round." A contains()-at-centre probe
        # can't catch a real regression here: the bore radius is 3.05mm,
        # so even a 2mm X shift of one side still lands the probe point
        # inside the (moved) cavity. Measure each side's actual cavity
        # centre independently via ray-casting instead, and compare them
        # to each other -- not to the PlateGeometry.mag_xs list both
        # sides are naively built from in the naive version above.
        result = build_plate()
        g, solid = result.geometry, result.solid
        z = g.plate_z / 2
        for nominal_x in g.mag_xs:
            front_centre = _cavity_center_x(solid, 0.5, z, nominal_x)
            back_centre = _cavity_center_x(solid, g.plate_y - 0.5, z, nominal_x)
            assert front_centre == pytest.approx(nominal_x, abs=0.05)
            assert back_centre == pytest.approx(front_centre, abs=0.05)

    def test_between_front_magnet_bores_is_solid(self):
        result = build_plate()
        g, solid = result.geometry, result.solid
        mid_x = (g.mag_xs[0] + g.mag_xs[1]) / 2
        assert solid.contains([(mid_x, 0.5, g.plate_z / 2)])[0]

    def test_bottom_corner_magnet_bores_are_cavities(self):
        result = build_plate()
        g, solid = result.geometry, result.solid
        pts = [
            (mx, my, 1.0)
            for mx in (g.bottom_mag_inset_x, g.plate_x - g.bottom_mag_inset_x)
            for my in g.bottom_mag_ys
        ]
        assert not any(solid.contains(pts))

    def test_stacking_groove_is_a_cavity_at_every_corner(self):
        result = build_plate()
        g, solid = result.geometry, result.solid
        pts = [
            (mx, my, g.stack_h / 2) for mx in g.stack_xs for my in g.stack_ys
        ]
        assert not any(solid.contains(pts))

    def test_stacking_groove_depth_matches_stack_h(self):
        # the groove is documented as stack_h deep -- verify that exact
        # depth on the mesh via ray casting, not the box coordinates used
        # to cut it (a past bug added a stray 0.1 mm overcut at the top).
        result = build_plate()
        g, solid = result.geometry, result.solid
        origin = [[g.stack_xs[0], g.stack_ys[0], -1.0]]
        direction = [[0, 0, 1]]
        locs, _, _ = solid.ray.intersects_location(origin, direction)
        first_hit_z = min(locs[:, 2])
        assert first_hit_z == pytest.approx(g.stack_h, abs=1e-6)

    def test_stacking_rib_is_solid_above_the_top_face(self):
        result = build_plate()
        g, solid = result.geometry, result.solid
        pts = [
            (mx, my, g.plate_z + g.stack_h / 2)
            for mx in g.stack_xs for my in g.stack_ys
        ]
        assert all(solid.contains(pts))

    def test_nothing_above_the_stacking_rib(self):
        result = build_plate()
        g, solid = result.geometry, result.solid
        pt = [(g.stack_xs[0], g.stack_ys[0], g.plate_z + g.stack_h + 0.5)]
        assert not solid.contains(pt)[0]

    def test_magnet_bore_to_stack_groove_wall(self):
        # documented at 1.85 mm (README.md, jig_plate_base.py comments).
        # Measured by ray-casting the actual mesh, not by recomputing the
        # wall from PlateGeometry fields (bottom_mag_inset_x, stack_inset_x,
        # etc.) -- those are passthroughs of the *inputs*, so a bug that
        # only shifts the real boolean cut (and not the returned metadata)
        # would be invisible to an arithmetic-only check like that.
        result = build_plate()
        g, solid = result.geometry, result.solid
        # probe just inside the groove's Y edge nearest the bore -- the
        # narrowest point of the wall, since the bore is a circle whose X
        # extent (at a given Y) widens as Y approaches the bore's own
        # centre, and the groove's Y range doesn't reach that centre.
        y = g.stack_ys[0] + (g.stack_w + g.stack_play) / 2 - 0.01
        z = 0.75  # inside both the groove's Z range [0, stack_h] and the
                  # bottom-corner bore's Z range
        origin = [[-1.0, y, z]]
        direction = [[1.0, 0.0, 0.0]]
        locs, _, _ = solid.ray.intersects_location(origin, direction)
        xs = sorted(locs[:, 0])
        groove_far_edge, bore_near_edge = xs[2], xs[3]
        wall = bore_near_edge - groove_far_edge
        assert wall == pytest.approx(1.85, abs=0.02)


class TestGeometryPositions:
    """CLAUDE.md design constraints that must not regress."""

    @pytest.mark.parametrize("mag_count_x", [2, 3, 4, 5])
    def test_magnet_bores_symmetric_about_x_centreline(self, mag_count_x):
        geom = build_plate(mag_count_x=mag_count_x).geometry
        centre = geom.plate_x / 2
        offsets = sorted(abs(x - centre) for x in geom.mag_xs)
        if len(offsets) % 2:
            # an odd count has one bore exactly on the centreline
            assert offsets[0] == pytest.approx(0.0, abs=1e-9)
            offsets = offsets[1:]
        for a, b in zip(offsets[0::2], offsets[1::2]):
            assert a == pytest.approx(b, abs=1e-9)

    def test_stack_positions_match_expected_values(self):
        # literal expected values, not the same formula/fields build_plate()
        # itself used to compute them -- a real regression check.
        geom = build_plate().geometry
        assert geom.stack_xs == (4.0, 242.0)
        assert geom.stack_ys == (4.0, 214.0)

    def test_stack_positions_independent_of_magnet_layout(self):
        a = build_plate(mag_inset_x=50.0, mag_count_x=2).geometry
        b = build_plate(mag_inset_x=20.0, mag_count_x=6).geometry
        assert a.stack_xs == b.stack_xs
        assert a.stack_ys == b.stack_ys

    def test_bottom_corner_magnet_positions_match_expected_values(self):
        geom = build_plate().geometry
        assert geom.bottom_mag_inset_x == 12.0
        assert geom.bottom_mag_ys == [5.0, 213.0]


class TestPurity:
    """build_plate() must have no side effects -- no file I/O, no argv."""

    def test_no_new_files_in_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        build_plate()
        assert list(tmp_path.iterdir()) == []
