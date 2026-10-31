import csv

import pytest

from ck.language_audit import lep_groups


def test_language_ranking_uses_lep_rows_and_preserves_sampling_margins(tmp_path):
    labels, data = tmp_path / "labels", tmp_path / "data"
    with labels.open("w") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["Table ID", "Indent", "Unique ID", "Label", "Universe"],
            delimiter="|",
        )
        writer.writeheader()
        for identifier, language in (("003", "Synthetic A:"), ("006", "Synthetic B:")):
            writer.writerow(
                {
                    "Table ID": "B16001",
                    "Indent": "1",
                    "Unique ID": "B16001_" + identifier,
                    "Label": language,
                    "Universe": "Synthetic population",
                }
            )
            writer.writerow(
                {
                    "Table ID": "B16001",
                    "Indent": "2",
                    "Unique ID": "B16001_" + str(int(identifier) + 2).zfill(3),
                    "Label": 'Speak English less than "very well"',
                    "Universe": "Synthetic population",
                }
            )
    data.write_text(
        "GEO_ID|B16001_E003|B16001_E005|B16001_M005|B16001_E006|B16001_E008|B16001_M008\n"
        "0100000US|9999|10|2|20|15|3\n"
    )
    groups = lep_groups(data, labels)
    assert [group["language"] for group in groups] == ["Synthetic B", "Synthetic A"]
    assert [group["estimate"] for group in groups] == [15, 10]
    assert groups[0]["margin_of_error"] == 3
    data.write_text(data.read_text().replace("|10|", "|-666666666|"))
    with pytest.raises(ValueError, match="suppressed"):
        lep_groups(data, labels)
