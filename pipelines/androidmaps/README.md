# Android roads-and-places maps

`ck android-map` regenerates OBF maps from cataloged OSM sources with the original
OsmAnd map creator JARs. Source archives are checksum-verified and remain unchanged.
Run inside the pinned Python build container with networking disabled:

```sh
ck android-map --state RI --osm-id geofabrik_ri \
  --output build/androidmaps/RI --epoch 1793401527
ck android-howto --output build/androidmaps/HOW_TO --epoch 1793401527
```

The filter retains configured road classes, road restrictions, named places and
the approved public-place categories. It removes excluded infrastructure tags,
other POI categories and source-user metadata. Untagged reference geometry stays
so roads and area members remain connected. Public schools and libraries need
explicit public ownership/operator tags in this OSM layer; the separate directory
uses NCES and IMLS records.

Turn-restriction relations and their referenced objects are retained. The initial
Rhode Island extract lacked way 722137578, referenced by restriction 10001982.
The catalog pins the original OSM API's full-way snapshot as a supplemental input.
`osmium apply-changes` combines the pinned inputs before filtering. An integrity
check fails on missing nodes, ways or relation members; it does not discard a
restriction to make the check pass. Source supplements and mappings live in
`settings.yaml` and are part of the recorded provenance.

The creator reads its OBF date from the filtered input's fixed mtime. Inspection
must find map, routing and POI indexes and the expected epoch. Wall-clock stderr
logs stay outside the generation pin. Each payload includes the filtered source
database and ODbL attribution. Two clean Linux amd64 runs produced identical OBF,
source PBF, attribution and generation-manifest hashes for this sample.

`complete: true` records completion of those data checks for the requested state.
Catalog review markers still block placement pending source-pin review and device
checks. The import guides remain incomplete and visibly identify their pending
phone checks. Both languages have one-page phone and print versions; every Spanish
page carries the unreviewed machine-translation notice.

The full planner selects one map method for all eight variants. In `auto` mode,
unconfirmed prebuilt terms or an overflow on any variant select roads-and-places
generation before other placement changes. `config/build.yaml` can explicitly
select `roads_places`. Assembly uses the plan's exact item list.

Only Rhode Island has a confirmed source mapping so far. Nationwide source pins,
large-state splitting, APK/signing/source verification and physical import/GPS
checks remain outstanding. See `docs/build-machine.md` for local resources and
staged build guidance.

Publisher references:

- https://osmand.net/docs/technical/map-creation/create-offline-maps-yourself/
- https://osmand.net/docs/technical/map-creation/how-to-inspect-an-obf/
- https://osmand.net/docs/user/personal/import-export/
- https://docs.osmcode.org/osmium/latest/osmium-tags-filter.html
- https://docs.osmcode.org/osmium/latest/osmium-apply-changes.html
