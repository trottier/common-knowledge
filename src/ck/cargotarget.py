"""Interpret Cargo's target-filtered normal/build tree without granting approval."""

import re
from collections import defaultdict


def target_tree(metadata: dict, tree: str) -> dict:
    """Bind Cargo tree output to metadata IDs; do not select metadata-only nodes.

    Input tree format: --edges normal,build --prefix depth --format '{p}|{f}'.
    Cargo metadata may expose additional feature-unified dependencies. The tree,
    rather than a naive walk through those nodes, determines this source set.
    """
    packages = {package["id"]: package for package in metadata["packages"]}
    identities = defaultdict(list)
    for package in packages.values():
        identities[package["name"], package["version"]].append(package["id"])
    nodes = {node["id"]: node for node in metadata["resolve"]["nodes"]}
    root = metadata["resolve"]["root"]
    if root not in packages or root not in nodes:
        raise ValueError("Cargo metadata has no resolved root package")
    selected, stack, edges, features = set(), [], {}, defaultdict(set)
    root_seen = False
    for line in tree.splitlines():
        match = re.fullmatch(r"(\d+)(\S+) v([^\s|]+)([^|]*)\|(.*)", line)
        if not match:
            raise ValueError(f"Unexpected Cargo tree line: {line!r}")
        depth, name, version, _, feature_text = match.groups()
        depth = int(depth)
        candidates = identities[name, version]
        if len(candidates) != 1:
            raise ValueError(f"Missing or ambiguous Cargo metadata identity: {name} {version}")
        identifier = candidates[0]
        if depth > len(stack):
            raise ValueError("Cargo tree depth skips a parent")
        if depth == 0:
            if root_seen or identifier != root:
                raise ValueError("Cargo tree must contain exactly its resolved root")
            root_seen = True
        else:
            parent = stack[depth - 1]
            matching = [dep for dep in nodes[parent]["deps"] if dep["pkg"] == identifier]
            kinds = [
                kind
                for dep in matching
                for kind in dep["dep_kinds"]
                if kind["kind"] in {None, "build"}
            ]
            if not kinds:
                raise ValueError("Cargo tree edge lacks a normal/build metadata declaration")
            edges[parent, identifier] = {
                "parent": parent,
                "dependency": identifier,
                "metadata_normal_build_declarations": kinds,
            }
        stack = stack[:depth] + [identifier]
        selected.add(identifier)
        feature_text = feature_text.removesuffix(" (*)")
        features[identifier].update(part for part in feature_text.split(",") if part)
    if not root_seen:
        raise ValueError("Cargo tree is empty")
    return {
        "root": root,
        "selected_package_ids": sorted(selected),
        "metadata_only_package_ids": sorted(set(packages) - selected),
        "selected_features": {key: sorted(features[key]) for key in sorted(selected)},
        "edges": [edges[key] for key in sorted(edges)],
        "selection": "Cargo tree --target TARGET --edges normal,build",
        "native_compilation_performed": False,
        "binary_membership_proven": False,
        "human_license_or_pin_approval": False,
    }
