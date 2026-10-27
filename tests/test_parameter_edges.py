"""Edge cases of build_plate() parameter validation: label width vs
plate_y, non-finite or overflowing numbers, and insets past the middle."""
import pytest

from jig_plate_base import build_plate

LONG_LABEL = "Jig Plate Longer Label Here"  # branding about 70.6 mm wide


def test_label_checked_against_plate_y_only_with_side_branding():
    with pytest.raises(ValueError, match="plate_y"):
        build_plate(plate_y=50, label=LONG_LABEL)
    # only the top face carries the label, so plate_y doesn't bound it
    result = build_plate(plate_y=50, side_branding=False, label=LONG_LABEL)
    assert result.solid.is_watertight


def test_label_wider_than_plate_x_still_rejected_without_side_branding():
    with pytest.raises(ValueError):
        build_plate(side_branding=False, label="W" * 60)


@pytest.mark.parametrize("value", [10**400, -(10**400), float("inf"),
                                   float("nan")],
                         ids=["huge", "huge-negative", "inf", "nan"])
def test_non_finite_or_overflowing_number_is_value_error(value):
    with pytest.raises(ValueError, match="plate_x must be finite"):
        build_plate(plate_x=value)


def test_overflowing_int_in_another_parameter_names_it():
    with pytest.raises(ValueError, match="mag_d must be finite"):
        build_plate(mag_d=10**400)


@pytest.mark.parametrize("name,value", [
    ("mag_inset_x", 123.0), ("mag_inset_x", 140.0),
    ("stack_inset_x", 123.0), ("stack_inset_x", 140.0)])
def test_inset_at_or_past_half_the_plate_is_rejected(name, value):
    with pytest.raises(ValueError, match=f"{name} .* less than half"):
        build_plate(mag_count_x=2, **{name: value})


def test_insets_below_half_still_ascend():
    g = build_plate(mag_count_x=2, mag_inset_x=100.0).geometry
    assert g.mag_xs[0] < g.mag_xs[1]


def test_thin_plate_is_rejected_by_a_bore_before_the_rib_is_checked():
    # The fit check has no Z-minimum test of its own for the stacking rib
    # (it stands proud and starts at plate_z): the bore checks, which come
    # first, already need plate_z >= mag_depth + 0.8 >= 1.6, and the front
    # and back bores need mag_d + 1.6. This pins that invariant: a plate
    # just below the smallest accepted thickness fails on a bore, never
    # on a rib, and the smallest accepted thickness builds.
    smallest = 6.1 + 1.6  # default mag_d, plus a wall above and below
    kw = dict(side_branding=False)
    with pytest.raises(ValueError, match="front push-fit bore"):
        build_plate(plate_z=smallest - 0.01, **kw)
    assert build_plate(plate_z=smallest, **kw).geometry.plate_z == smallest
    # smallest printable bore: below mag_d + 1.6 = 2.4 a bore still fails
    # first, never the rib
    for plate_z in (0.8, 1.0, 1.6, 2.0, 2.39):
        with pytest.raises(ValueError, match="bore"):
            build_plate(plate_z=plate_z, mag_d=0.8, mag_depth=0.8, **kw)
