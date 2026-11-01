"""Capture the publisher's four Android Cargo source trees without compiling.

Run with the locked project Python environment. The exact publisher Rust image
must already be pulled into the chosen Docker context. Network access is disabled
for every container. Work directories must be new, and cache bytes stay unchanged.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tomllib
from pathlib import Path

from ck.cargocheck import CRATES_IO, archive_text, audit_cargo_sources
from ck.cargotarget import target_tree
from ck.catalog import load_catalog
from ck.generated import cached_input


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--docker-context", required=True)
    args = parser.parse_args()
    args.work = args.work.resolve()
    if args.work.exists():
        raise ValueError("Use a new work directory; prior scratch sources are never reused")
    items = load_catalog(args.root)
    app_source = items["bitchat_android_source"]
    prefix = "tools/arti-build/"
    full = audit_cargo_sources(items, app_source.id, prefix + "Cargo.lock", args.cache)
    local_ids = {record["source_id"] for record in full["local_packages"]} - {app_source.id}
    if len(local_ids) != 1:
        raise ValueError("This publisher recipe expects one Arti upstream source archive")
    upstream = items[local_ids.pop()]
    args.work.mkdir(parents=True)
    scratch, raw = args.work / "scratch", args.work / "raw"
    scratch.mkdir()
    raw.mkdir()
    original = {}
    with tarfile.open(cached_input(app_source, args.cache)) as archive:
        for relative in [
            "Cargo.toml",
            "Cargo.lock",
            "src/lib.rs",
            "Dockerfile",
            "TOOLCHAIN.env",
            "rust-toolchain.toml",
            "build-arti.sh",
        ]:
            original[relative] = archive_text(archive, prefix + relative)
        if any("/tools/arti-build/patches/" in member.name for member in archive):
            raise ValueError("Publisher patches need explicit audited preparation before capture")
    match = re.search(
        r"^FROM (rust:\S+@sha256:[0-9a-f]{64})$", original["Dockerfile"].decode(), re.M
    )
    if not match:
        raise ValueError("Publisher Rust Docker base is not pinned by digest")
    image = match[1]
    environment = dict(
        line.split("=", 1) for line in original["TOOLCHAIN.env"].decode().splitlines()
    )
    toolchain = tomllib.loads(original["rust-toolchain.toml"].decode())["toolchain"]
    if toolchain["channel"] != environment["RUST_VERSION"]:
        raise ValueError("Publisher Rust version declarations disagree")
    targets = toolchain["targets"]
    if set(targets) != {
        "aarch64-linux-android",
        "armv7-linux-androideabi",
        "i686-linux-android",
        "x86_64-linux-android",
    }:
        raise ValueError("Publisher Android target list changed")
    with tarfile.open(cached_input(upstream, args.cache)) as archive:
        top = archive.getmembers()[0].name.split("/")[0]
        archive.extractall(scratch / "upstream", filter="data")
    shutil.move(scratch / "upstream" / top, scratch / "arti")
    wrapper = scratch / "arti/arti-android-wrapper"
    for relative in ["Cargo.toml", "Cargo.lock", "src/lib.rs"]:
        target = wrapper / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(original[relative])
    vendor = scratch / "vendor"
    vendor.mkdir()
    for record in full["registry_packages"]:
        item = items[record["source_id"]]
        with tarfile.open(cached_input(item, args.cache)) as archive:
            top = archive.getmembers()[0].name.split("/")[0]
            archive.extractall(vendor, filter="data")
        directory = vendor / top
        files = {
            str(path.relative_to(directory)): digest(path.read_bytes())
            for path in directory.rglob("*")
            if path.is_file() and path.name != ".cargo-checksum.json"
        }
        dump(directory / ".cargo-checksum.json", {"files": files, "package": item.sha256})
    (scratch / ".cargo").mkdir()
    (scratch / ".cargo/config.toml").write_text(
        '[source.crates-io]\nreplace-with = "verified-vendor"\n'
        '[source.verified-vendor]\ndirectory = "/audit/vendor"\n[net]\noffline = true\n'
    )
    base = [
        "docker",
        "--context",
        args.docker_context,
        "run",
        "--rm",
        "--pull=never",
        "--network=none",
        "--platform=linux/amd64",
        "--cpus=1",
        "--memory=1g",
        "--env=CARGO_HOME=/audit/cargo-home",
        "--env=CARGO_NET_OFFLINE=true",
        "--env=RUSTUP_TOOLCHAIN=" + environment["RUST_VERSION"],
        "--volume",
        str(scratch) + ":/audit",
        "--workdir=/audit",
        image,
    ]
    receipts = []

    def run(arguments, name):
        result = subprocess.run(base + arguments, capture_output=True, check=False)
        (raw / name).write_bytes(result.stdout)
        (raw / (name + ".stderr")).write_bytes(result.stderr)
        receipts.append(
            {
                "arguments": arguments,
                "stdout_sha256": digest(result.stdout),
                "stderr_sha256": digest(result.stderr),
                "stderr": result.stderr.decode(),
                "exit_code": result.returncode,
            }
        )
        if result.returncode:
            raise ValueError("Offline Cargo query failed: " + result.stderr.decode())
        return result.stdout.decode()

    versions = {
        name: run([name, "--version", "--verbose"], name + "-version.txt")
        for name in ["cargo", "rustc"]
    }
    if not versions["rustc"].startswith("rustc " + environment["RUST_VERSION"] + " "):
        raise ValueError("Actual Rust compiler differs from publisher version")
    bindings = {
        (r["name"], r["version"]): r for r in full["registry_packages"] + full["local_packages"]
    }
    results = {}
    for target in targets:
        manifest = ["--manifest-path", "/audit/arti/arti-android-wrapper/Cargo.toml"]
        metadata = json.loads(
            run(
                [
                    "cargo",
                    "metadata",
                    "--offline",
                    "--locked",
                    "--format-version=1",
                    "--filter-platform",
                    target,
                ]
                + manifest,
                "metadata-" + target + ".json",
            )
        )
        tree = run(
            [
                "cargo",
                "tree",
                "--offline",
                "--locked",
                "--target",
                target,
                "--edges=normal,build",
                "--prefix=depth",
                "--format={p}|{f}",
            ]
            + manifest,
            "tree-" + target + ".txt",
        )
        cfg = run(["rustc", "--print=cfg", "--target", target], "cfg-" + target + ".txt")
        selection = target_tree(metadata, tree)
        records = []
        for package in metadata["packages"]:
            if package["id"] not in selection["selected_package_ids"]:
                continue
            binding = bindings[package["name"], package["version"]]
            if package["source"] not in {None, CRATES_IO}:
                raise ValueError("Unexpected Cargo source kind")
            records.append(
                {
                    "package_id": package["id"],
                    "name": package["name"],
                    "version": package["version"],
                    "catalog_source_id": binding["source_id"],
                    "source_archive_sha256": items[binding["source_id"]].sha256,
                    "registry": package["source"] is not None,
                }
            )
        results[target] = {
            **selection,
            "packages": sorted(records, key=lambda x: x["package_id"]),
            "rustc_cfg": cfg.splitlines(),
        }
        print(target, len(records), "normal/build packages", flush=True)
    if digest((wrapper / "Cargo.lock").read_bytes()) != full["lock_sha256"]:
        raise ValueError("Cargo changed the publisher lockfile")
    if (wrapper / "target").exists():
        raise ValueError("Unexpected Cargo build output directory")
    selected_registry = {
        r["catalog_source_id"]
        for result in results.values()
        for r in result["packages"]
        if r["registry"]
    }
    all_registry = {r["source_id"] for r in full["registry_packages"]}
    dump(
        args.output,
        {
            "schema_version": 1,
            "application_source_id": app_source.id,
            "application_source_sha256": app_source.sha256,
            "arti_source_id": upstream.id,
            "arti_source_sha256": upstream.sha256,
            "lock_sha256": full["lock_sha256"],
            "image": image,
            "tool_versions": versions,
            "publisher_input_sha256": {name: digest(data) for name, data in original.items()},
            "container_policy": {
                "network": "none",
                "platform": "linux/amd64",
                "cpus": 1,
                "memory": "1g",
            },
            "full_lock_registry_source_ids": sorted(all_registry),
            "selected_android_registry_source_ids": sorted(selected_registry),
            "excluded_from_all_android_normal_build_trees": sorted(
                all_registry - selected_registry
            ),
            "targets": results,
            "command_receipts": receipts,
            "scratch_source_rewrites": [],
            "derived_scratch_files": [".cargo/config.toml", "vendor/*/.cargo-checksum.json"],
            "lockfile_unchanged": True,
            "native_compilation_performed": False,
            "binary_membership_proven": False,
            "source_graph_changed": False,
            "human_license_or_pin_approval": False,
        },
    )


if __name__ == "__main__":
    main()
