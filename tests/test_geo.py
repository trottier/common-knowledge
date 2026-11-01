import math
import re

import pytest
from shapely import MultiPolygon, box

from ck.geo import Frame, dms, mercator, unproject

SETTINGS = dict(width=1000, height=1200, columns=6, rows=8, padding=0.08, maxzoom=14)


def test_projection_roundtrip_and_frame_grid():
    for lon, lat in [(-179.5, 52.0), (-70.5, 41.0), (144.8, 13.5)]:
        x, y = mercator(lon, lat)
        result = unproject(x, y)
        assert math.isclose(result[0], lon, abs_tol=1e-10)
        assert math.isclose(result[1], lat, abs_tol=1e-10)
    frame = Frame.fit(box(-2, -2, 2, 2), **SETTINGS)
    assert re.fullmatch(r"[A-F][1-8]", frame.grid(0, 0))
    with pytest.raises(ValueError, match="outside"):
        frame.grid(30, 30)


def test_dateline_county_fits_the_short_extent():
    shape = MultiPolygon([box(178, 51, 179, 52), box(-179, 51, -178, 52)])
    frame = Frame.fit(shape, **SETTINGS)
    assert frame.shifted and frame.east - frame.west < 0.03
    assert frame.grid(178.5, 51.5)[0] < frame.grid(-178.5, 51.5)[0]


def test_dms_labels_carry_rounding_and_parse():
    assert dms(12 + 59 / 60 + 59.9 / 3600, "lat") == "13°00′00″N"
    frame = Frame.fit(box(-72, 41, -71, 42), **SETTINGS)
    for label in frame.labels()["vertical"] + frame.labels()["horizontal"]:
        match = re.fullmatch(r"(\d+)°(\d{2})′(\d{2})″([NSEW])", label["dms"])
        assert match
        degrees, minutes, seconds = map(int, match.groups()[:3])
        assert minutes < 60 and seconds < 60
        value = degrees + minutes / 60 + seconds / 3600
        if match[4] in "SW":
            value = -value
        assert abs(value - float(label["decimal"][:-1])) < 0.0002
