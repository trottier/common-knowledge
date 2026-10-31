# Public places pipeline

`ck directory --state RI --state-fips 44 --output build/directory/RI`
builds phone and print PDFs from checksum-verified cache inputs. Set a development
`SOURCE_DATE_EPOCH` or use `--epoch`. The command accepts any Census state or
territory code and checks that its FIPS code agrees with the pinned reference.
Use `--osm-id geofabrik_us` for the national extract once its pin is confirmed.

Inputs currently implemented:

- NCES EDGE public-school workbook (2024–25).
- IMLS FY2024 public-library outlet CSV, Windows-1252; central and branch outlets.
- Geofabrik OSM PBF, filtered with `osmium tags-filter`; public hospital,
  urgent-care, pharmacy, fire, police and post-office points/areas.
- NWS station JSON embedded in its published JavaScript data file. Parsing uses
  JSON, never JavaScript execution. Operational status and transmitter power are
  discarded. Frequencies remain the publisher's exact strings.
- USAGov state emergency agency links, extracted without scripts or page assets.
- TIGER/Line county boundaries for spatial assignment. Cartographic boundary
  files explicitly prohibit precise geographic analysis and are not used for joins.

Source bytes stay unchanged in the SHA-256 cache. The pipeline regenerates original
directory PDFs from those inputs and keeps source IDs and as-of versions per entry.
Every page says “May help; not confirmed open.” Coordinates are rounded for display;
the unrounded source coordinates remain in the build-only `places.json` for the atlas.
Repeated IDs deduplicate extracts. Boundary ties use the lowest county GEOID.
Places outside the requested state's boundaries do not enter that state's directory.

The pipeline rejects excluded infrastructure tags before recording a public place.
It never imports general government offices, event shelters or distribution points.
Names are escaped before Markdown/Jinja processing. Missing addresses are labeled;
addresses and coordinates are not inferred or geocoded.

The first build is intentionally incomplete: FCC broadcast imports, FEMA county
hazard summaries and atlas page/grid references still need implementation and
verified inputs. `generation.json` records `complete: false`; the assembler rejects
such outputs. `--atlas-index` can supply the atlas's exact place-ID references.
No development directory is eligible for emergency distribution.

The source catalog also records human pin-review and immutable-mirror blockers.
Some agencies publish only mutable URLs; checksums prevent accepting changed bytes,
but a future clean rebuild needs the pinned bytes to remain downloadable.
