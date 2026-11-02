"""ZIP overview labels use supplied Census interior points and preserve codes."""

from xml.etree import ElementTree

from shapely.geometry import box, mapping

from ck.countyproof import zip_overlay


def test_zip_areas_have_boundaries_and_labels_at_supplied_locations():
    codes = ["02806", "02809", "02885"]
    data = {
        "policy": {"zcta_colors": ["#7852a9", "#07856b", "#c17a09"]},
        "zip_areas": [
            {
                "code": code,
                "geometry": mapping(box(i * 20, 0, i * 20 + 18, 18)),
                "label_point": [i * 20 + 9, 9],
            }
            for i, code in enumerate(codes)
        ],
    }
    areas, labels, reserved = zip_overlay(data, box(0, 0, 100, 100), lambda x, y: (x, y))
    parsed = ElementTree.fromstring("<svg>" + areas + labels + "</svg>")
    text = parsed.findall("text")
    assert [element.text for element in text] == codes
    assert [float(element.attrib["x"]) for element in text] == [9, 29, 49]
    assert len(reserved) == 3
    assert len([path for path in parsed.findall("path") if "fill-opacity" in path.attrib]) == 3
    assert "02806-02885" not in labels
