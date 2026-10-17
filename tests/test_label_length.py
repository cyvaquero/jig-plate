"""An over-long label is rejected before any glyph is rendered, and the
cheap check never rejects a label that builds."""
import time

import pytest

from jig_plate_base import _text_width, build_plate

# found by bisection on the default plate: the longest run of the widest
# common glyph that builds; one more is rejected by the exact width check
LONGEST_W = 44


def test_huge_label_rejected_fast():
    t0 = time.perf_counter()
    with pytest.raises(ValueError, match="far wider than plate_x"):
        build_plate(label="W" * 6000)
    # was about 5.5 s; the bound is generous so it is not flaky
    assert time.perf_counter() - t0 < 2.0


def test_longest_buildable_label_still_builds():
    result = build_plate(label="W" * LONGEST_W)
    assert result.solid.is_watertight


def test_label_just_over_the_limit_is_still_rejected():
    with pytest.raises(ValueError):  # either check
        build_plate(label="W" * (LONGEST_W + 1))


def test_cheap_check_is_looser_than_the_exact_one():
    """The precheck only fires above plate_x; every label that builds is
    far below it (the branding needs 9 mm more than the text)."""
    assert _text_width("W" * LONGEST_W, 4.0) < 246.0 - 9.0
