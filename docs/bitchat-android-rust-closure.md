# Rust source selection for the four Android targets

The exact publisher wrapper selects a union of **345 registry packages**, plus
43 Arti path packages and the wrapper, across its four Android normal/build
dependency trees. The complete Cargo lockfile still contains 465 registry
packages and those 44 local packages. Both inventories are preserved as distinct
facts; no catalog entry, source-graph edge, or review hold is changed.

| Android target | Registry packages | Arti + wrapper | Total selected | Metadata-only extras |
| --- | ---: | ---: | ---: | ---: |
| `aarch64-linux-android` | 315 | 44 | 359 | 37 |
| `armv7-linux-androideabi` | 316 | 44 | 360 | 37 |
| `i686-linux-android` | 344 | 44 | 388 | 36 |
| `x86_64-linux-android` | 343 | 44 | 387 | 36 |

The [target evidence](evidence/bitchat-android-cargo-targets.json) records every
selected package's actual Cargo ID, source-archive checksum, catalog ID, and
target membership. It also records command-output hashes, target cfg values,
per-target feature/edge inventory hashes, and the exact tool/input identities.
The [full-lock evidence](evidence/bitchat-rust-sources.json) remains available.

## Exact inputs and an offline replay

The publisher app source pins Arti commit
`ba421ece1acb47e5c554c2bfa043cc9156451bab`, the committed wrapper lockfile, its
explicit dependency features, and Rust 1.95.0. The audit copies the original
wrapper manifest, lockfile, and `src/lib.rs` into the exact upstream workspace,
following the publisher's directory arrangement. It applies no patches and
rewrites no publisher source files. All 465 registry archives are verified and
copied into scratch vendor directories. Only Cargo's checksum metadata and
offline source-replacement configuration are generated.

The tool image is the publisher Dockerfile's own official Rust image:

```text
rust:1.95.0-slim-bookworm@sha256:d7482085ff5b415f84dba5647ae71606650bdef00db7aeb69f4b3d170c3e4082
```

Its OCI index and Linux amd64 manifest were verified against their registry
digests. The installed Cargo and rustc binaries match the binary bytes in Rust's
official 1.95.0 component archives; those archive checksums come from the
publisher distribution manifest, itself checked against its SHA-256 file.
The actual tools report Cargo 1.95.0 and rustc 1.95.0.

Each metadata container has networking disabled and is capped at one CPU and
1 GiB. Queries use `--offline --locked`. There is no compilation, build-script
execution, SDK installation, or APK build. The lockfile remains unchanged, and
no Cargo build-output directory is created.

Two independent scratch preparations produced byte-identical stdout for all
12 target queries: metadata, normal/build tree, and rustc cfg for each target.
The second preparation used the batch Docker context. To reproduce with the
locked project Python environment and a populated verified cache:

```sh
rtk proxy docker --context colima-common-knowledge-batch pull --platform linux/amd64 rust:1.95.0-slim-bookworm@sha256:d7482085ff5b415f84dba5647ae71606650bdef00db7aeb69f4b3d170c3e4082
rtk proxy uv run --locked python tools/audit_android_cargo_sources.py \
  --root . --cache cache --work build/android-cargo-audit-clean \
  --docker-context colima-common-knowledge-batch \
  --output build/android-cargo-audit-clean/audit.json
```

Use a new work directory. The tool refuses to reuse old scratch state, pull
container images implicitly, change a lockfile, or accept an unexpected
publisher target/toolchain declaration.

## Why both Cargo outputs matter

`cargo metadata --filter-platform` contains 36–37 packages per target that are
absent from the normal/build tree. Examples include native-tls/OpenSSL and
additional schema/elliptic-curve packages. Walking metadata's normal/build
declarations alone over-selects those feature-unified dependencies.

The audit therefore uses the actual
[`cargo tree --target … --edges normal,build`](https://doc.rust-lang.org/cargo/commands/cargo-tree.html)
output to select sources, then binds those entries and edges to metadata IDs.
The parser rejects ambiguous identities and dev-only edge declarations. It
retains metadata-only packages as a separate inventory rather than silently
including them in the selected source set.

Conversely, a name that sounds like test infrastructure is not grounds for
exclusion. Both x86 trees include `criterion-cycles-per-byte` through tor-proto's
normal `cfg(any(target_arch = "x86", target_arch = "x86_64"))` dependency, and
therefore include criterion and its selected dependencies. There are 31 package
versions whose membership differs among the four target trees.

These are Cargo's normal/build source dependency selections. Cargo documents
that its tree is an approximation of compiler build units. The audit does not
claim that each selected package contributes retained machine code to the
published `.so`, or prove the existing native binaries can be rebuilt.

## Notice-audit changes in scope

Seven of the 17 packages from the earlier notice audit are absent from every
selected Android tree: both objc2 packages, both r-efi versions, valuable, and
both Windows import-library crates. They are also absent from every target's
filtered metadata. Their full-lock catalog records and original notice evidence
remain intact.

In particular, the objc2 publisher's Apple-SDK caveat concerns source packages
outside this selected four-target set. This evidence supports reviewing whether
those package archives need to accompany an Android source release; it grants
no new redistribution right and clears no approval automatically.

The selected Android set still contains amplify_syn, cesu8, and void, so their
specific notice/grant questions remain relevant. Priority-queue's license files
are already present in its registry archive. ANES and its recovered notice
companion are relevant to the x86 variants. The target evidence maps all 17
cases to the actual selected targets.

## Proposed source graph and remaining work

The [graph proposal](evidence/bitchat-android-source-graph-proposal.json) retains
the 345-package registry union and flags the other 120 registry inputs for a
target-aware source-release decision. The selected registry archives total
29,870,697 bytes; the other 120 total 59,681,313 bytes. The unchanged Arti archive
is still needed for all 43 path packages. No source artifact is dropped.

Before applying any narrower release graph, separate full-lock inventory
validation from release-graph reachability. The existing full-lock auditor
expects all locked packages to be reachable through its audit root. Keep all
465 original catalog records and an explicit full-lock audit for restoration
and alternate targets; validate the Android selection separately. Do not
relabel lockfile completeness as Android runtime membership.

Original notices still need delivery beside the app. Whole upstream archives
can contain additional licensed files even when their packages are unselected;
this audit does not change those archives or their obligations. The exact native
and APK rebuilds, Java/Android source closure, remaining publisher notice
questions, reviewed computed pins, and existing human/legal and device gates
remain separate work.
