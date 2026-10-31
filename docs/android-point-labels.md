# Settlement labels and complete road references

The Android roads-and-places filter keeps settlement names from OSM **nodes**.
It does not import place polygons or administrative boundary relations.
The county atlas separately supplies Census county boundaries. Highway ways,
approved public POIs and turn restrictions remain part of the Android map.
A road or POI with a `place` tag keeps its approved road/POI tags without
retaining that polygon's place classification.

The initial native selection uses node place tags. After the tag allowlist and
sensitive-site exclusions run, a second native selection keeps untagged objects
only when retained features reference them. An excluded standalone POI therefore
leaves no unused point or polygon behind. Untagged nodes needed by a retained
road remain, with contributor UID, username and changeset metadata removed.

Diagnostic checks on the full pinned extracts found that the older policy pulled
in incomplete island and administrative polygons. A node-label diagnostic had
complete Oceania references. The U.S. diagnostic retained eleven missing way
references in border turn restrictions. The production pipeline still runs
`osmium check-refs --check-relations` and fails on any missing member.

Eleven full-way XML snapshots were downloaded from the primary OSM API, totaling
16,203 bytes. Every way and node timestamp in these snapshots predates the pinned
extract's 2026-10-29 replication timestamp. The exact responses, including all
referenced nodes, have SHA-256 pins in `catalog/geodata.yaml`. The configured
U.S. supplements are merged before filtering. Their original bytes remain in the
cache; the source manifest binds every supplement hash. Independently reviewing
these computed pins and preserving immutable source snapshots remain release
gates. No incomplete road restriction is silently removed.

The tiny regression fixtures cover a place polygon with a missing foreign member,
a retained city label, a road carrying a place tag, an excluded standalone POI,
and a missing turn-restriction member that must still fail. They also cover a
supplement that repairs a restriction without modifying the original download.
Full production source generation and repeated national map builds remain
required; diagnostic files are not placed on drives.

Tool references: [Osmium tag filtering](https://docs.osmcode.org/osmium/latest/osmium-tags-filter.html),
[reference checking](https://docs.osmcode.org/osmium/latest/osmium-check-refs.html),
and the [OpenStreetMap API](https://wiki.openstreetmap.org/wiki/API_v0.6).
