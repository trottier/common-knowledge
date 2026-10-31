# Offline laptop map

Variant 3's collection includes `laptop/1_OPEN_MAP.html` and
`2_US_ROADS.pmtiles`. Open the HTML file, then choose the map file in the same
folder. No server, installation, browser extension or internet connection is
required. The universal atlas PDFs remain the phone map format.

The browser reads byte ranges through PMTiles' [FileSource](https://pmtiles.io/typedoc/classes/FileSource.html).
MapLibre's pinned 5.24.0 classic browser distribution runs from a local file.
Its glyph manager uses installed fonts when the style omits a glyph URL. This
avoids font downloads; the computer may lack fonts for some place names.
The 5.x classic distribution was selected because it needs no module loader
when opened with `file://`. Publisher JavaScript and CSS remain byte-identical.
Only Common Knowledge's own interface is bundled with the pinned Bun version.

## Data pipeline

Freeze the source recipe before generating data. Prepare and pin the checked
56-jurisdiction `protomaps_us` input first, as described in
[national-atlas.md](national-atlas.md). Run inside the pinned build container:

```sh
ck laptop-tiles --generated build/generated --output build/laptop-data \
  --epoch "$SOURCE_DATE_EPOCH"
```

The policy in `pipelines/laptopmap/settings.yaml` permits only roads,
settlement labels and water polygons through zoom 12. The filter rebuilds each
tile's property dictionaries, removing rejected features and their unused
strings. It removes POI, building and infrastructure layers, contact fields,
and excluded infrastructure details. Retained geometry integers are unchanged.
The result is an ODbL derivative database with attribution and regeneration
provenance. Low-zoom tiles extend beyond jurisdiction boundaries as map context.
The map contains no live closures, service availability or event shelters.

Overlapping source tiles must match exactly. A disk-backed index deduplicates
them before conversion. Sorted tile IDs, exact-content deduplication and gzip
with a fixed timestamp make the archive deterministic. High-zoom payloads are
skipped before reading, rather than decoding the full atlas input set. The
size budget fails explicitly; no zoom or jurisdiction is silently dropped.

Pin the measured generation manifest as `laptop_roads_places` and put that
output at `build/generated/laptop_roads_places`. Then run:

```sh
ck laptop-viewer --generated build/generated --cache cache \
  --output build/laptop-viewer --epoch "$SOURCE_DATE_EPOCH"
```

The bundle contains the map, interface, unchanged SDK distributions, publisher
notices and `SOURCE.TXT`. The region selector derives its bounds from the
verified state basemap headers. Each external SDK/archive/license input is
pinned in `catalog/laptopmap.yaml`; `sdk.yaml` identifies exact archive members.
The publisher lockfiles provide the dependency versions. Runtime dependency
notices are included even when the distributed SDK already bundles them.
MurmurHash's complete README supplies its MIT notice. JSONLint 2.0.2 omitted a
license file; its publisher's later
[MIT license addition](https://github.com/mapbox/jsonlint/commit/524533a0ddeeff6f29dab38af1644e30ec74d3c5)
is separately pinned and included. Independent pin/notice review remains open.

The dataset ID, epoch, source version and size check catches a wrong selection;
it is not a cryptographic integrity check. Use `MANIFEST.SHA256` to verify the
drive. The viewer rejects unrelated request URLs, and its content policy
disables connections. It stores no location or file choice between sessions.

## Verification

```sh
bun run --cwd pipelines/laptopmap test
python tools/laptop_fixture.py build/laptop-fixture --cache cache
cd pipelines/laptopmap
CK_VIEWER_DIR=../../build/laptop-fixture/viewer/files bun run test:browser
```

Install development packages with `bun install --frozen-lockfile`. The browser
test uses the pinned Playwright package; install its Chromium test browser with
`bunx playwright install chromium`, or set `CK_CHROMIUM_EXECUTABLE` to an
existing Chrome executable. Playwright's CLI uses Node as required by that
test tool. The shipped viewer has no Node or Bun dependency.

The synthetic fixture uses real checksum-checked SDKs, with explicit synthetic
map data and temporary catalog overrides. It never changes production pins.
The browser test opens `file://`, rejects a wrong file, renders the selected
archive, exercises coordinates/region/zoom controls, selects the file again,
and fails on HTTP requests, script errors or content-policy violations.

The first full filtered dataset has 667,936 retained tiles from 753,983 unique
input tiles and is 618,293,897 bytes. Its packaged viewer opened in automated
Chrome on this Mac with no HTTP requests. This is not a physical USB test or
a claim of Windows, Linux, Firefox or Safari coverage. Complete those manual
checks before release, including the USB-A adapter laptop.
