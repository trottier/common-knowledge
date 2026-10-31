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
