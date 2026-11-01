# Bounded large-state Android maps

The California development conversion exhausted its 6,144 MiB Java heap while
reading the complete state input. Increasing the heap is not the only build path:
the additive split converter limits the input to each sequential conversion and
keeps the original publisher JARs unchanged.

`android-map --split` requires a pinned, prepared state extract. It applies the
same national roads-and-places filter as the single-map converter, then splits
that complete filtered state source along its longer coordinate extent. Child
regions overlap by the amount configured in `pipelines/androidmaps/split.yaml`.
The configured 32 MiB source target and 3,072 MiB Java heap are operational bounds,
not guarantees about the publisher's peak memory use. Maximum depth and part
limits fail explicitly rather than dropping a region.

Each region uses Osmium's smart extraction with complete relation members and
passes `osmium check-refs --check-relations`. Before conversion, all final regional
sources are merged, and `osmium diff --quiet` compares their union against the
complete state source. That comparison covers every object and attribute, not
just counts or bounding boxes. A missing road, place, turn-restriction member, or
changed union fails the build. Empty clips can be omitted only when they contain
no objects. The complete filtered source database ships alongside the map parts
for ODbL compliance.

The unchanged creator converts parts sequentially. Every part keeps the exact
build epoch and has a bound inspection, and the state set must contain map,
routing, and POI indexes. Its `parts.json` binds each map name to its regional
source, source hash, byte count, object counts, and inspection. `coverage.json`
records the exact-union check. Failure logs survive temporary-directory cleanup
in an adjacent `.failure` directory; retries retain previous diagnostics.

The additive collector accepts the frozen single-map recipe and the new split
recipe together. It checks every payload and intermediate hash, the complete
part sequence, regional byte bounds, source counts, and the exact source union
again. Before publishing, a separate guard selects every regional object's ID
from the complete original source with `osmium getid`, then compares that
reference with the region using `osmium diff`. A merged union alone can hide a
conflicting duplicate object, because Osmium does not define which conflicting
copy survives. The per-region comparison rejects altered or extra objects,
including overlapping duplicates, and rechecks complete object references before
the temporary collection is published.
Its receipts and collector recipe are bound in the national generation record.
It still requires every Census jurisdiction before publishing a national
set. The original `androidmaps.py`, `mapextract.py`, and their config files are
unchanged, so existing single-map, national-source, and state-extract fingerprints
remain valid. A newly measured split pin causes the preparation adapter to pass
`--split` for that jurisdiction.

After `rtk proxy make build-container`, a host invocation is:

```sh
rtk proxy docker run --rm --network=none --platform linux/amd64 \
  --volume "$PWD:/source:ro" --volume "$PWD/cache:/cache:ro" \
  --volume "$PWD/build:/artifacts" --workdir /source --env PYTHONPATH=src \
  --entrypoint /workspace/.venv/bin/ck common-knowledge-build:dev \
  android-map --split --state CA --osm-id geofabrik_us --cache /cache \
  --prepared /artifacts/generated/android_extract_ca --prepared-id android_extract_ca \
  --output /artifacts/generated/android_map_ca --epoch "$SOURCE_DATE_EPOCH"
```

Use a fresh output directory for each independent repeat, then review and pin
the measured generation record before collecting. The catalog must already bind
the prepared state extract. No map-content, source-pin, application-rights, or
physical-device approval is granted by this command.

Large states ship several `.obf` files and a `STATE_PARTS.txt` list. Import every
listed part and keep the set together. Complete ways and restrictions overlap
the computational boundaries, but real-device map import, GPS behavior, and
navigation across parts still need physical testing. The import guides retain
that explicit review marker; use the PDF atlas if the application fails or a
route is unsafe. Do not claim that automated source coverage establishes safe
navigation or reader compatibility. The OsmAnd APK's separate restricted-asset
hold remains in place.

The publisher's OBF inspector can combine indexes, but its documented edition
date format has minute precision. Separate parts preserve arbitrary build-epoch
seconds without rewriting generated headers. See the primary
[Osmium extraction manual](https://docs.osmcode.org/osmium/latest/osmium-extract.html),
[object-difference manual](https://docs.osmcode.org/osmium/latest/osmium-diff.html),
[ID-selection manual](https://docs.osmcode.org/osmium/latest/osmium-getid.html),
[merge duplicate rules](https://docs.osmcode.org/osmium/latest/osmium-merge.html),
and [upstream inspector source](https://github.com/osmandapp/OsmAnd-tools/blob/b601887fc5603bd65f7eafc9d7d32c42c572a342/java-tools/OsmAndMapCreatorUtilities/src/main/java/net/osmand/obf/BinaryInspector.java).
