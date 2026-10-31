# County atlas

The Python stage prepares county viewports and coordinate grids. The `atlas`
target of `Dockerfile.build` renders local PMTiles with MapLibre Native. Python
then composes the checked PNGs into a bookmarked PDF and a directory index.

Use `make atlas-check` for the Bun tests and an original synthetic fixture through
the real native renderer. The test container has no network. Bun installs the
locked packages and runs scripts; Node runs the native addon because its release
targets Node's ABI. This preserves the specified native runtime.

The development sequence, inside the appropriate pinned containers, is:

```sh
ck directory --seed --state RI --state-fips 44 --output build/directory/RI-seed
ck atlas prepare --state RI --state-fips 44 \
  --directory build/directory/RI-seed --directory-id directory_seed_ri \
  --places-id census_places_ri --output build/atlas/RI --epoch 1793401527
python3 tools/extract_atlas.py --root . --jobs build/atlas/RI/jobs.json \
  --source-file cache/6956cdf4b143984a31e060faaa32848c74a71903135b5a7f8989c218ece8795d \
  --output build/generated/protomaps_ri
# Pin the measured generation manifest, payload size and input IDs in catalog/maps.yaml.
ck atlas prepare --state RI --state-fips 44 \
  --directory build/directory/RI-seed --directory-id directory_seed_ri \
  --places-id census_places_ri --basemap-id protomaps_ri \
  --output build/atlas/RI --epoch 1793401527
bun run render /absolute/container/path/build/atlas/RI/jobs.json
ck atlas compose --jobs build/atlas/RI/jobs.json --output build/atlas/RI-composed
```

These commands must see the same absolute input paths across stages. Mount the
repository at `/source` in both containers and set their working directories to
`/source` for Python and `/workspace/pipelines/atlas` for rendering. Keep networking
disabled except during the explicit fetch and tile extraction stages. Extracted
tiles, fonts, rasters and PDFs stay in ignored cache/build directories.

The extraction script records its source, region, CLI archive pin and output
checksum. `--source-file` verifies the complete pinned planet's size and SHA-256
before extracting without networking. Pass several paths after `--jobs` to
extract a batch of states, checking the 139 GB source only once; the output then
contains a folder per state. An HTTP range extraction cannot certify the whole
source and remains incomplete. The 2026-10-30 planet has been independently
checked against the publisher's BLAKE3 checksum and its SHA-256 is now pinned.
Immutable preservation, source-pin review, directory exceptions and nationwide
coverage remain release gates. Incomplete artifacts cannot enter assembled images.

Full TIGER/Line geometry determines county membership and city insets. Generalized
cartographic boundaries are not used for spatial analysis. Dateline viewports
unwrap longitudes before fitting. Grid references refer to the location dot;
displaced numbers have leader lines. Directory references choose the most detailed
available map and use its actual PDF page, not the render-job position.

Before tile layout, the renderer loads the pinned font’s glyphs in one batch.
This makes glyph allocation repeatable instead of depending on tile completion
order. The discarded warm-up geometry never enters a shipped map.

The atlas template, source code, dependency locks and container inputs enter the
pipeline fingerprint. Changing any requires preparation and rendering again.
The compositor checks every raster hash and fails on missing or duplicate pages.
`settings.yaml` holds raster dimensions, inset threshold and the national byte
budget. The full build must compare the sum of all state outputs to that budget.
Physical phone checks, national coverage and a full atlas capacity measurement
remain required; the Rhode Island sample does not establish those claims.
