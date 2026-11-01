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
thread count, SSE2 CPU baseline and 128-bit software vector width are fixed in
the container. Initial Rhode Island renders differed by small text-edge values
between processes. Priming the pinned font's glyphs removed the differences
observed in that sample, but the first national repeat exposed further tiny
text-edge differences in Oregon. The old warmup removed its source and layer,
allowing primed glyph resources to leave the resident cache.

The revised warmup supplies one label per supported character, avoiding shaping
between adjacent code points. Its world tile remains resident while real map
views render. A viewport guard prevents the original priming geometry at 0°, 0°
from entering a published map. Three fresh Oregon runs now match all 47 map
views, including city and dense-area insets. Their composed PDFs and complete
generation manifests also match. At epoch `1793404800`, the PDF is 20,976,743
bytes with SHA-256
`84e4b9d5b593145baf42d3e462cbc21d99b72734828f97c68dd3082f3d436ab5`.
The subsequent historical national repeat is recorded below; corrected-source
and full-image repeats are still required.

Jobs now bind a hash of the production JavaScript recipe. Both the native
renderer and PDF composer reject a different code hash. This catches a cached
container that predates a source change. The render record includes the actual
runtime settings and installed tool versions. The native fixture checks both
repeated frames and fresh processes. Stable image resource names also keep
temporary build directories out of PDF object names and identifiers.

Two separate Rhode Island preparation, native-render and composition runs on
Linux arm64 produced byte-identical PDFs and generation manifests, using epoch
`1793401527`, five county maps and one city inset. The measured PDF was 8,686,060
bytes, with SHA-256:

```text
3aca88ad59790abf371281ccf13997c37b0d6c2bb5290428f199cbbe7cc72ba0
```

This is development evidence for that older pinned sample. The first complete
national atlas now covers all 56 Census jurisdictions with verified basemaps;
see [national-atlas.md](national-atlas.md). The older Rhode Island atlas and
directory samples retain `complete: false` and cannot enter assembled images.
The historical national repeat now matches; corrected-source rendering,
full-image reproducibility and phone usability remain unconfirmed. Changes to
inputs or the pipeline require new measured pins.

Two fresh native renders and PDF compositions now match for every jurisdiction
of the historical 254,062-place snapshot. Both complete collections passed the
county-bookmark and place-reference checks: 56 jurisdictions, 3,235 counties,
4,112 map views and 1,880,010,193 placed bytes at epoch `1793404800`.
The canonical generation-manifest SHA-256 is
`4e32d47c79fdc8af18d5b8f91072eb5e3473fb2f14037ae79fd08a52e2b911fb`.
Each collected payload was also checked against its recorded size and SHA-256.
See [the measured receipt](evidence/atlas-repeat-historical.json).

This is renderer reproducibility evidence for that exact earlier corpus. It
does not include the later Puerto Rico and U.S. Virgin Islands source repair,
whose corrected point snapshot contains 254,873 places. Its separate atlas and
directory repeats remain in progress. Do not replace corrected-source catalog
pins with these historical measurements or treat them as full-image evidence.

The Android roads-and-places sample has also been built twice in separate
Linux amd64 containers. Both runs produced the same 28,809,801-byte placed payload,
including the OBF, its filtered OSM source database and attribution. The OBF
SHA-256 is `e7721846333184fd9b4e6c81300820fed1d847926aa03b314fa35e4f1749511b`.
Reference integrity and map/routing/POI indexes passed; physical phone tests and
source-pin review remain outstanding. Its data-completion flag records those
technical checks, and its catalog review markers continue to block placement.

For interrupted large provisional inputs, `tools/resume_download.py` checks each
HTTP range, byte count and source ETag before appending a complete chunk. This
does not certify the input. Verify the publisher checksum and compute SHA-256,
then submit the measured pin for review before it becomes a release input.

The verification URL is assigned in `config/build.yaml`; its deployment receipt
is [recorded separately](evidence/pages-deployment.json). The release epoch and
measured production capacity remain unset. Never substitute the current time
for an unset release epoch. The assembler records system, Python, and
generated-content tool versions in image `VERIFY.TXT`.
