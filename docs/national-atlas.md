# National atlas build

The atlas uses the pinned national point snapshot, Census county analysis
boundaries, all 56 publisher state/territory place files, the Noto font and a
whole verified Protomaps planet. The place files come from the
[2025 Census PLACE index](https://www2.census.gov/geo/tiger/TIGER2025/PLACE/).
All downloads have measured sizes and computed SHA-256 pins. Their human pin
reviews remain open; downloading data does not approve publication.

Run these stages inside the pinned build environments. Use one epoch for every
stage and freeze the recipe before preparing jobs. Preliminary jobs have no
basemap and cannot be published as complete atlases.

```sh
ck atlas prepare-all --directory build/national-points --cache cache \
  --output build/atlas/preliminary --epoch "$SOURCE_DATE_EPOCH"
```

The command validates the shared point payload and county data once, then
writes `STATE/jobs.json` and `STATE/region.geojson` for every jurisdiction in the
national Census snapshot. `--states RI DE` selects an explicit development
subset. State codes and Census FIPS codes must agree. Each state requires its
own `census_places_<lowercase-state>` catalog input.

Use the build-tool stage's `tools/extract_atlas.py` with every preliminary job
and `--source-file cache/<protomaps_planet-sha256>`. It hashes the entire local
planet once, checks its size and PMTiles header, then extracts the viewports
without networking. Remote range extracts remain incomplete. A batch creates
one `generation.json` and `files/STATE.pmtiles`, plus bound per-state provenance.
Hard links avoid a second physical copy of each extracted basemap in the batch.
Pin the measured batch as `protomaps_us`; its declared inputs must include all
state place inputs used by the jobs.

Prepare final jobs with that generated input:

```sh
ck atlas prepare-all --directory build/national-points --cache cache \
  --basemap-id protomaps_us --generated build/generated \
  --output build/atlas/final --epoch "$SOURCE_DATE_EPOCH"
```

The generated input must contain exactly one matching `STATE.pmtiles` for each
requested state. A different state's file is never used as a fallback. The
point snapshot and basemap epoch must match the requested atlas epoch.

Render each job with the pinned native atlas container, then use `ck atlas
compose --jobs ... --output ...`. State jobs can run independently with bounded
concurrency. Keep total container memory below the resources assigned to the
build environment. See [build-machine.md](build-machine.md) for this Mac's
dedicated container profile and resource limits.

Dense counties get an overview with source-location dots and spatially split
detail maps. `max_points_per_page` bounds numbered legends. Records sharing
coordinates use distinct legends on repeated views; their coordinates stay
unchanged. Detail pages preserve every source point, including across the
antimeridian. City insets also split when necessary. County overviews keep one
bookmark per source county; inset/detail pages add no county bookmarks.

The native PNG is checked against the renderer manifest, then encoded to JPEG
at the pinned `image_quality` setting for PDF embedding. Point numbers, leader
lines, county outlines and the coordinate grid remain vector elements.
Adjust the quality in settings and rebuild if the measured national budget
overflows; no state or source place is silently dropped.

Collect all composed jurisdictions with `ck atlas collect --directory ...
--outputs ... --output ... --epoch ...`. Collection requires the complete
jurisdiction list, matching recipe/input pins and epoch, exact Census county
bookmark coverage, and a bound page/grid reference for every national place.
It rejects changed indexes, invalid page/grid values, duplicate points, missing
states and a total PDF size above `max_total_bytes`. The resulting national
`place-index.json` is the shared input for final state directories.

Pin the measured set as `national_atlas` only after successful collection.
Complete input and output checks do not replace legal/source pin review,
physical phone checks or repeated builds from the final release tag.

The first complete viewport batch contains 4,112 map pages across all 56
jurisdictions. Its whole-planet-verified basemaps total 10,543,561,690 bytes of
build inputs, pinned as `protomaps_us`. A Delaware native-render/composition
check produced its five map pages with county bookmarks and point references.
This does not establish complete nationwide PDF rendering. The full point-name
font check found four names requiring Cherokee, Arabic or Chinese coverage.
The shared [geographic font policy](geographic-fonts.md) now covers those names
and fails on unsupported characters. Font-aware national rendering is underway.
