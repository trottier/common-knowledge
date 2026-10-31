# Reproducible builds

## Scaffold environment

All authoritative checks and package builds run inside `Dockerfile.build` using
Linux x86-64. `make check` and `make package` select `linux/amd64` explicitly.

The Python image is the official publisher's `python:3.12.16-slim-bookworm`,
pinned to the multi-platform index digest:

```text
sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337
```

The uv image is Astral's `ghcr.io/astral-sh/uv:0.9.24`, pinned to:

```text
sha256:816fdce3387ed2142e37d2e56e1b1b97ccc1ea87731ba199dc8a25c04e4997c5
```

Both digests were read from the official registries with
`docker buildx imagetools inspect`. The Python index identifies version
`3.12.16-slim-bookworm`. Refreshing either pin requires an explicit reviewed
change. The build backend is `uv_build==0.9.24`, matching the copied uv version.
Direct test dependencies are pinned, and `uv.lock` pins the dependency graph
and artifact hashes. Container installs use `uv sync --locked --no-editable`.

Publisher references:

- [Docker Official Python image](https://hub.docker.com/_/python)
- [Astral's Docker integration and digest pinning](https://docs.astral.sh/uv/guides/integration/docker/)
- [uv build backend](https://docs.astral.sh/uv/concepts/build-backend/)
- [Ruff](https://docs.astral.sh/ruff/)
- [pytest](https://docs.pytest.org/en/stable/)

The container sets UTC, a UTF-8 locale and disables Python bytecode writes and
automatic interpreter downloads. Its dependency installation uses the network;
checks and package generation then run with `--network=none`. The build backend
is bundled with uv, so `uv build --offline` can build the scaffold distributions.

System packages now come from the verified Debian and Debian Security snapshot
endpoints dated `20261028T000000Z` in `config/debian.sources`. APT validates the
signed index, and the snapshot fixes the package dependency graph. The container
records all Debian package versions in `/opt/ck-tool-versions.txt`.

The Noto font inputs are recorded by immutable publisher commit, size, license
proof and computed SHA-256 in `catalog/fonts.yaml`. The bootstrap verifies each
file before placing it in `/opt/ck-fonts/<sha256>`. No font binaries enter git.
Publisher HTTPS downloads without published checksums still require human review
of the pinned hashes before release; the catalog records that pending review.

PDF rendering uses the release epoch or an explicitly supplied development epoch,
never the current time. Both PDF metadata dates and the PDF identifier derive
from fixed inputs. The renderer denies network resources and files outside the
build's asset/font inputs. PDFs are tagged; formal PDF/UA conformance is not
claimed without validation. Arabic shaping, bookmarks, links, sizes, metadata
and repeated PDF hashes are covered by container tests.

## Development images and atlas

The development assembler now normalizes FAT timestamps, copies in sorted order,
checks the manifest against files read back from the image, and hashes the raw
and compressed images. A regression test compares two small development images,
including Unicode filenames. Two full clean sample-profile builds are still
required; a passing development fixture does not establish that result.

The atlas uses a separate Ubuntu 24.04 stage with the snapshot in
`config/ubuntu.sources`. Node 22.23.4 and Bun 1.3.11 are copied from digest-pinned
publisher images. `catalog/buildtools.yaml` records GitHub's published SHA-256
digests for the MapLibre Native addon and PMTiles CLI. Bun's lockfile records the
JavaScript dependency artifacts. Install hooks are disabled; the bootstrap checks
the native release before installing it. Node is required for the addon's ABI;
Bun handles dependency installation, scripts and new JavaScript tests.

The native renderer denies network resources. Mesa software rendering and its
thread count are fixed in the container. Initial Rhode Island renders differed
by small text-edge values between processes. Priming the pinned font's glyphs
before tile layout removed the observed differences. The native fixture checks
both repeated frames and fresh processes. Stable image resource names also keep
temporary build directories out of PDF object names and identifiers.

Two separate Rhode Island preparation, native-render and composition runs on
Linux arm64 produced byte-identical PDFs and generation manifests, using epoch
`1793401527`, five county maps and one city inset. The measured PDF was 8,686,060
bytes, with SHA-256:

```text
3aca88ad59790abf371281ccf13997c37b0d6c2bb5290428f199cbbe7cc72ba0
```

This is development evidence for that pinned sample. National coverage, full
basemap verification, Linux x86-64 full-image reproducibility and phone usability
remain unconfirmed. Generated samples retain `complete: false` and cannot enter
assembled images. Changes to inputs or the pipeline require new measured pins.

The release epoch, production capacity and verification URL remain unset until
the configuration and release steps. Never substitute the current time for an
unset release epoch. Record all tool versions in image `VERIFY.TXT` when the
assembler is implemented.
