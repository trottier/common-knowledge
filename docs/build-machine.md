# Build machine

The reference full-build machine is Linux x86-64 with at least 16 cores, 64 GB RAM
and 1 TB free SSD, Java 17 or newer, and Node 20 or newer. Those specifications
provide room for large map generation and cached inputs. The repository's pinned
containers supply the actual tool versions.

The project publisher asked to continue on the available Mac. Its task-specific
Colima profile is `common-knowledge`, configured with 6 virtual CPUs and 16 GiB RAM,
Rosetta for Linux amd64 containers, and a writable mount of this repository. Its
Docker context is `colima-common-knowledge`. The existing `colima` context and its
containers were not restarted or reconfigured. The new context was created with
`--activate=false`, so commands must select it explicitly.

The local Docker CLI is 29.2.1, but its existing Buildx plugin is 0.12.0. The
plugin defaults to API 1.43, below the new daemon's minimum. For local builds,
scope the compatible API setting to the command:

```sh
env DOCKER_CONTEXT=colima-common-knowledge DOCKER_API_VERSION=1.44 make build-container
```

The API setting does not change the global Docker context or install a replacement
plugin. Run authoritative image builds as `linux/amd64`. Local arm64 checks are
useful development evidence; they do not establish matching full-image hashes
on x86-64.

Keep inputs in `cache/` by checksum and build output on the mounted host SSD.
Never copy datasets into a Docker build context. Build states and variants in
stages, retaining verified final artifacts and deleting only task-owned temporary
databases. The planet PMTiles input alone is 139,202,898,553 bytes for the pinned
2026-10-30 publisher build; plan disk space before retaining eight image trees
and eight raw images simultaneously.

OsmAnd map creation uses the heap limit in
`pipelines/androidmaps/settings.yaml`. The initial Rhode Island run uses 2 GiB.
Large states may need a larger heap or smaller, overlapping geographic extracts;
their split pipeline and national measurements remain unfinished. Do not label
a partial state complete or silently discard roads when memory is exhausted.
The CLI currently accepts only states with confirmed source mappings.

The production USB capacity remains a measured-input requirement. The publisher's
32 GB answer supplies the nominal target, and does not replace measured usable
bytes. Full-image capacity checks must keep that distinction.

## Staged image builds

Prepare and review the exact catalog inputs and generated artifacts first. Keep
raw downloads in `cache/<sha256>` and each generated item in
`build/generated/<item-id>/`, including its `generation.json`. The assembler
checks those files against the catalog; copying an old prototype directory is
not sufficient when its pipeline fingerprint has changed.

`make sample` builds variants 1 and 3 twice. Each pass renders a fresh core and
assembles a fresh filesystem tree. Both raw image hashes, compressed hashes and
manifest hashes must agree before `build/sample/build-manifest.json` is written.
The workflow's preflight runs on a hosted runner; the larger build uses a Linux
x86-64 runner labeled `common-knowledge`. No such runner is currently registered.
Set the repository variable `CK_DATA_ROOT` to its prepared data directory, or use
the default `/var/lib/common-knowledge`. The workflow does not install a runner
or enable untrusted pull requests to execute on a personal machine.

On the Mac, the same sample command can run directly through the dedicated
Docker context. No Actions runner is needed for a local build:

```sh
rtk proxy env DOCKER_CONTEXT=colima-common-knowledge DOCKER_API_VERSION=1.44 make sample
```

`make full` requires a clean checkout at the configured version tag, all release
review gates, a confirmed release epoch and measured production capacity. It
builds all eight variants twice, one at a time. It retains compressed images,
external checksums, per-image manifests and the final build manifest. Raw image
files and temporary assembled trees are removed after verification to conserve
disk space. Use `ck build-profile --keep-raw` when the extra disk space is
available. To copy a retained image to a drive, decompress its `.img.zst` and
check the resulting `.img` against its published `.img.sha256`.

Neither target downloads or drops missing content during image assembly. Run
`ck check-profile --profile sample` or `--profile full` for the outstanding
catalog and review blockers. Failures leave no successful build manifest; keep
failed output for diagnosis and choose a new output directory for the retry.

`make release-assets` applies the review gates, downloads pinned corresponding
GPL sources, builds all eight development images, and packages the PDFs,
catalog lock, source archives and checksums under `build/release/`. Source
archives are verified as archives, and each asset must be below 2 GB. The tag
workflow publishes only after all assets have uploaded into a draft release.

`make site` builds a static verification page from published release manifests
and reviewed full-build manifests under `verification/`. The Pages workflow
collects all published release manifests and verifies their checksums, including
when triggered after the Release workflow. Unpublished candidates are labeled
as development content; a successful site build is not release approval.
