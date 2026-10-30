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

## What remains

Pinned tools establish the environment; this step does not establish byte-for-byte
drive image reproducibility. Image generation, fixed artifact timestamps, PDF
normalization, manifests and two clean sample builds arrive later in the work
order. No reproducibility exception or passing image-hash test is claimed here.

The release epoch, production capacity and verification URL remain unset until
the configuration and release steps. Never substitute the current time for an
unset release epoch. Record all tool versions in image `VERIFY.TXT` when the
assembler is implemented.
