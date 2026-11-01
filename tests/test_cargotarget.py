"""Check the boundary between metadata inventories and Cargo's selected tree."""

import pytest

from ck.cargotarget import target_tree


def metadata():
    return {
        "packages": [
            {"id": name, "name": name, "version": "1.0.0"}
            for name in ["root", "normal", "build", "dev", "metadata_extra"]
        ],
        "resolve": {
            "root": "root",
            "nodes": [
                {
                    "id": "root",
                    "deps": [
                        {"pkg": "normal", "dep_kinds": [{"kind": None, "target": None}]},
                        {"pkg": "build", "dep_kinds": [{"kind": "build", "target": None}]},
                        {"pkg": "dev", "dep_kinds": [{"kind": "dev", "target": None}]},
                        {
                            "pkg": "metadata_extra",
                            "dep_kinds": [{"kind": None, "target": None}],
                        },
                    ],
                },
                *[
                    {"id": name, "deps": []}
                    for name in ["normal", "build", "dev", "metadata_extra"]
                ],
            ],
        },
    }


def test_tree_controls_selection_and_keeps_build_dependencies():
    result = target_tree(
        metadata(),
        "0root v1.0.0 (/audit/root)|\n"
        "1normal v1.0.0|default\n"
        "1build v1.0.0 (proc-macro)|derive\n"
        "1normal v1.0.0|extra (*)\n",
    )
    assert result["selected_package_ids"] == ["build", "normal", "root"]
    assert result["metadata_only_package_ids"] == ["dev", "metadata_extra"]
    assert result["selected_features"]["normal"] == ["default", "extra"]
    assert len(result["edges"]) == 2
    assert not result["binary_membership_proven"]
    assert not result["human_license_or_pin_approval"]


def test_dev_only_edge_is_rejected():
    with pytest.raises(ValueError, match="normal/build"):
        target_tree(metadata(), "0root v1.0.0|\n1dev v1.0.0|\n")


def test_source_identity_ambiguity_is_not_guessed():
    data = metadata()
    data["packages"].append({"id": "other-source", "name": "normal", "version": "1.0.0"})
    with pytest.raises(ValueError, match="ambiguous"):
        target_tree(data, "0root v1.0.0|\n1normal v1.0.0|\n")


@pytest.mark.parametrize(
    "tree",
    [
        "",
        "0normal v1.0.0|\n",
        "0root v1.0.0|\n2normal v1.0.0|\n",
        "0root v1.0.0|\n0root v1.0.0|\n",
        "0root v1.0.0|\n1unknown v1.0.0|\n",
        "root v1.0.0\n",
    ],
)
def test_invalid_or_incomplete_tree_is_rejected(tree):
    with pytest.raises(ValueError):
        target_tree(metadata(), tree)
