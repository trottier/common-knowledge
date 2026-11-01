# Public places pipeline

`ck directory --state RI --state-fips 44 --output build/directory/RI`
builds phone and print PDFs from checksum-verified cache inputs. Set a development
`SOURCE_DATE_EPOCH` or use `--epoch`. The command accepts any Census state or
territory code and checks that its FIPS code agrees with the pinned reference.
Use `--osm-id geofabrik_us` for the national extract once its pin is confirmed.

Build the atlas point seed first with `ck directory --seed`. That build emits
source data and a bound `places.json`, without directory PDFs or atlas page
references. Its catalog placement is build-only. The atlas consumes this seed;
the final directory consumes the atlas's `place-index.json` using both
`--atlas-index PATH` and `--atlas-id CATALOG_ID`. The index must match the
catalog-pinned atlas generation manifest and its epoch. This directed data flow
avoids making the atlas depend on the final directory that it must paginate.

Inputs currently implemented:

- NCES EDGE public-school workbook (2024–25).
- IMLS FY2024 public-library outlet CSV, Windows-1252; central and branch outlets.
- Geofabrik OSM PBF, filtered with `osmium tags-filter`; public hospital,
  urgent-care, pharmacy, fire, police and post-office points/areas.
- NWS station JSON embedded in its published JavaScript data file. Parsing uses
  JSON, never JavaScript execution. Operational status and transmitter power are
  discarded. Frequencies remain the publisher's exact strings.
- USAGov state emergency agency links, extracted without scripts or page assets.
- FCC LMS facility, service/status dictionaries, granted license versions and
  application locations. Import only AM/FM broadcast services. Follow explicit
  granted-license references when a renewal or assignment lacks coordinates;
  retain the exact reference filing in each entry. Geographic points must
  declare EPSG:4326. A granted construction permit supplies geometry only when
  an explicit granted-license reference points to it; a standalone permit
  never becomes a station entry. NAD27 degree fields, contact details, tower
  engineering and non-broadcast telecommunications are not imported.
- FEMA National Risk Index v1.20 (December 2025) county ratings, using hazard
  names from the dictionary in the same publisher ZIP. Preserve ratings as
  published; these are historical relative risk, not warnings or forecasts.
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

Builds without every source family, confirmed geographic references, county
profiles and atlas page/grid references remain explicitly incomplete. The
assembler rejects `complete: false`. `--atlas-index` supplies the atlas's exact
place-ID references; its bytes enter the recipe fingerprint and build audit.
Unlocatable records are reported rather than replaced with guessed coordinates.

The pinned FEMA table has 3,232 county records. Three Census county equivalents
have no published profile: Swains Island (60040), Rose Island (60030) and
Northern Islands Municipality (69085). Their source gaps remain visible and
require review. The Rhode Island FCC snapshot resolves all 54 licensed radio
facilities to 55 geographic references, including one multi-location filing.
The national import resolves 25,881 facilities to 25,963 references; 19 facilities
remain unlocatable under these rules and are listed in the rejection audit.
All national inputs still require pin review and immutable preservation.

The source catalog also records human pin-review and immutable-mirror blockers.
Some agencies publish only mutable URLs; checksums prevent accepting changed bytes,
but a future clean rebuild needs the pinned bytes to remain downloadable.
