"""Every enlarged sheet keeps a truthful scale bar inside its reserved area."""

import pytest

from ck.countyproof import scale_bar_geometry


@pytest.mark.parametrize("depth", range(6))
def test_scale_bar_uses_sheet_extent_and_fits_at_every_supported_inset_depth(depth):
    extent = 4750 / 2**depth
    metres, width = scale_bar_geometry(extent, 190, 40)
    assert 0 < width <= 40
    assert width / 190 == pytest.approx(metres / extent)
    assert 6 + width + 4 <= 54  # Background and ruler remain inside the label exclusion.


def test_invalid_scale_bar_reservation_fails():
    with pytest.raises(ValueError):
        scale_bar_geometry(100, 190, 190)
