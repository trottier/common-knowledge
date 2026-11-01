# National Android map preparation

Full maps use the publisher-verified U.S. parent for the states and D.C.
Puerto Rico and the U.S. Virgin Islands use their separate dated territory
extracts. American Samoa, Guam and the Northern Mariana Islands use the verified
Oceania parent. The choice is recorded in
`pipelines/androidmaps/national.yaml` and checked against the source pins.
The existing Rhode Island sample path keeps its dated state extract and pinned
turn-restriction supplement.

Run these commands inside the pinned Linux build environment with one fixed
epoch. Each command requires a new output directory. Source pins and physical
phone checks remain separate release gates.

First filter each large parent once:

```sh
ck android-source --osm-id geofabrik_us --cache cache \
  --output build/generated/android_source_us --epoch "$SOURCE_DATE_EPOCH"
ck android-source --osm-id geofabrik_oceania --cache cache \
  --output build/generated/android_source_oceania --epoch "$SOURCE_DATE_EPOCH"
ck android-source --osm-id geofabrik_puerto_rico --cache cache \
  --output build/generated/android_source_puerto_rico --epoch "$SOURCE_DATE_EPOCH"
ck android-source --osm-id geofabrik_virgin_islands --cache cache \
  --output build/generated/android_source_virgin_islands --epoch "$SOURCE_DATE_EPOCH"
```

The existing national roads/public-place allowlist strips excluded tags and
source user identifiers. Reference checks must pass, including relations.
An incomplete publisher restriction is an error requiring a pinned, documented
source correction; do not discard it or publish an incomplete map. Pin each
measured prepared source in its catalog entry before extracting states.

Extract one jurisdiction at a time to bound memory and avoid repeatedly hashing
the complete set of state inputs:

```sh
ck android-extract --prepared build/generated/android_source_us \
  --prepared-id android_source_us --states RI --cache cache \
  --output build/generated/android_extract_ri --epoch "$SOURCE_DATE_EPOCH"
```

The extraction uses the full Census county analysis geometries and Census
state codes. Its small configured padding is in coordinate degrees, not a
claimed distance in metres. Antimeridian extents are extracted on each side
and merged. Osmium's smart strategy completes ways and retained relations,
including turn restrictions whose connected road lies beyond a state boundary.
The result must pass `osmium check-refs --check-relations` and an extended
object-count audit. An empty clip must fail even when every reference check
passes vacuously. Each state mapping records its node, way and relation counts.

See the primary [Osmium extract manual](https://docs.osmcode.org/osmium/latest/osmium-extract.html)
for strategy and antimeridian behavior. Identifier bitsets make memory depend
on source IDs as well as the amount of data in a state. Keep extraction
concurrency bounded on the dedicated Mac VM. A state's output may include
connected geometry beyond the padded boundary; it is not a surveyed boundary.

Pin the measured state extract, then generate its OBF:

```sh
ck android-map --state RI --osm-id geofabrik_us --cache cache \
  --prepared build/generated/android_extract_ri --prepared-id android_extract_ri \
  --output build/generated/android_map_ri --epoch "$SOURCE_DATE_EPOCH"
```

Prepared sources must match their bound state mapping, source parent, recipe
and epoch. The map creator runs with the configured national Java heap; the
small-state sample keeps its smaller heap. The additive
[bounded large-state converter](large-android-maps.md) handles jurisdictions that
exceed the single-map heap. Its actual national measurements and physical checks
remain unfinished. The OBF set must contain map, routing and
POI indexes and the fixed edition timestamp. Each payload includes its modified
source database and attribution for ODbL compliance.

After all states are pinned, `ck android-collect --cache cache --outputs ...
--output ... --epoch ...` verifies every expected Census jurisdiction, payload,
source database and bound inspection/filter audit. It rejects missing or
duplicate states, changed pins, differing epochs/recipes and files that exceed
FAT32 limits. Its measured national set fulfills `android_roads_places` for the
planner; no state can be silently omitted.

These stages implement the build path. National source checks, OBF generation,
repeat builds and physical installation/import checks remain unfinished.
See [territory-source-coverage.md](territory-source-coverage.md) for the source
selection correction and its effect on existing development outputs.
The official APK also remains on the separate
[restricted-asset distribution hold](osmand-provenance.md).

## Measured development subset

At epoch 1793404800, separate map conversions match for nine jurisdictions:
American Samoa, Connecticut, D.C., Delaware, Guam, Northern Mariana Islands,
Puerto Rico, Rhode Island and U.S. Virgin Islands. Complete generation records,
placed payload hashes and intermediate audit hashes were checked in both outputs.
The measured records are in
[android-map-repeat-checkpoint.json](evidence/android-map-repeat-checkpoint.json).

The four completed U.S.-parent conversions have these sizes:

| Jurisdiction | OBF bytes | Total placed bytes, including ODbL source and notices |
| --- | ---: | ---: |
| Connecticut | 79,570,289 | 120,105,930 |
| D.C. | 11,299,984 | 15,678,758 |
| Delaware | 19,820,130 | 28,603,733 |
| Rhode Island | 18,911,104 | 28,513,484 |

These pairs reuse their pinned prepared sources and state extracts. They do not
establish two clean national pipeline builds, complete 56-jurisdiction coverage,
production capacity or phone installation/import/GPS usability. New Jersey and
the remaining maps are still building. The application rights hold is separate;
generated map measurements do not clear it. Final recipe freeze and named pin
review remain required.
