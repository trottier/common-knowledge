# Territory source coverage

An actual Virgin Islands Android clip from the U.S. parent contained no OSM
objects. It still passed reference checks: an empty file has no missing
references. The previous national point import also contained zero OSM places
in both Puerto Rico and the Virgin Islands, although their federal-source
places were present. Those results do not establish OSM coverage for either
territory.

Geofabrik lists both territories alongside the U.S. states, but its
[Central America overview](https://download.geofabrik.de/central-america.html)
identifies their inclusion in that geographic parent. The build now uses the
smaller individual territory extracts, rather than inferring coverage from
where links appear on a download page:

- [Puerto Rico](https://download.geofabrik.de/north-america/us/puerto-rico.html):
  dated 2026-10-29, 74,228,024 bytes, SHA-256
  `82c3e21506394d7eb91984363b6f80835f901d90551f2a8c24210352f203621c`.
- [U.S. Virgin Islands](https://download.geofabrik.de/north-america/us/us-virgin-islands.html):
  dated 2026-10-28, 3,122,136 bytes, SHA-256
  `dc0ff82695dda2d00cb17ec83d25e00f8e004bc83f9ebb13dba504277d1f1ccc`.

Both HTTPS downloads match their publishers' MD5 sidecars; their computed
SHA-256 pins and dates are recorded separately in the catalog. This is input
verification, not a human pin review or a claim that every public place appears
in OpenStreetMap.

Android maps and national directory points share the parent selection in
`pipelines/androidmaps/national.yaml`. Its explicit territory overrides take
precedence over the U.S. fallback. Unknown override sources fail validation.
The national point builder requires at least one matched public place from the
configured OSM source in every Census jurisdiction. It records each source and
count in both its build metadata and public source data. A jurisdiction with
federal records alone can no longer pass this coverage check.

Android extraction checks object counts as well as references before creating a
complete state manifest. Its real corrected Virgin Islands extract has 98,010
nodes, 12,367 ways and 30 relations. Puerto Rico has 1,530,005 nodes, 193,647 ways
and 591 relations at development epoch 1793404800. These are extraction counts,
not claims of complete roads, verified routes or a tested map app.

The old point snapshot and its descendant atlases/directories need regeneration.
Their measured payloads remain development evidence; successful layout, link and
repeat checks cannot repair missing source coverage. Corrected national point
generation, all resulting atlas page/grid references, national maps, independent
repeat builds and physical checks remain release gates.
