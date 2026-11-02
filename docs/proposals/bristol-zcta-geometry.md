# Bristol County ZCTA geometry intake

The official Census 2020 TIGERweb response contains exactly the three Bristol
County codes already found in the pinned 2020 county relationship table: `02806`,
`02809`, and `02885`. `catalog/postal.yaml` adds `census_zcta_bristol_2020` as a held,
`hub_only` prototype build input. No renderer, existing artifact pin, national
source graph, review status, or source epoch changes in this packet.

The unmodified GeoJSON is 16,717 bytes, SHA-256
`278db2981af844412c7c5668aa11251be0babd8c4a82940d0d916336815725ee`.
The repository SHA cache contains those exact bytes. The exact encoded request,
metadata pins, feature bounds, source areas, and audit results are recorded in
[the intake receipt](../evidence/bristol-zcta-intake-2026-11-01.json).

## Publisher provenance and display suitability

The [Census API documentation](https://www.census.gov/data/developers/data-sets/TIGERweb-map-service.html)
identifies `Census2020` as the decennial service directory. The actual
[layer 84 metadata](https://tigerweb.geo.census.gov/arcgis/rest/services/Census2020/tigerWMS_Census2020/MapServer/84)
identifies polygon ZCTAs with a January 1, 2020 vintage and U.S. Census Bureau
source credit. Its XML metadata agrees. The query selects only the three codes,
requests every polygon with EPSG:4326 output, and orders by `ZCTA5`. It requests
no simplification, precision reduction, or quantization. No server transfer-limit
flag or error was returned.

The [Census products guide](https://www.census.gov/programs-surveys/geography/guidance/tiger-data-products-guide.html)
classifies TIGERweb as detailed. This packet does not establish exact vertex
identity with the full TIGER/Line shapefile or survey accuracy. This is distinct
from the explicitly generalized `Generalized_TAB2020` service.

An initially inspected official 500K cartographic-boundary ZIP is preserved only
in the ignored cache and research receipts. Its embedded metadata forbids display
at scales larger than 1:500,000. It is not a county-rendering input and is not
added to the catalog. No national full-detail geometry archive was downloaded.

## Actual geometry checks

An offline container using the pinned existing tool image, one CPU, and a 2 GiB
memory cap rehashed the source, validated all three geometries with Shapely, and
checked their closed rings and Census interior points. Each feature has one
valid polygon ring. Counts are 158, 116, and 115 vertices, respectively.
The interior points lie within their corresponding polygons and can supply
label positions without inventing centroids or locality boundaries.

All three codes map solely to county `44001` in the existing relationship source.
Each feature's land and water area attributes exactly match that 2020 table.
These are attribute comparisons, not claims that planar GeoJSON areas equal
published geodesic source areas. Leading zeros remain strings. The geometry
covers the Census statistical area, including water, rather than an invented
shoreline-clipped postal boundary.

## Rights, attribution, and remaining review

The feature metadata credits the U.S. Census Bureau. Section 1.2 of the
[2020 technical documentation](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2020/TGRSHP2020_TechDoc.pdf)
explains the government-work copyright basis, allows reproduction of Census
materials, and asks for source credit. This supports the held `US-PD`
classification; it is not a named human rights approval.
The [API terms](https://www.census.gov/data/developers/about/terms-of-service.html)
provide attribution and nonendorsement conditions that remain part of review.
A derived map must identify its overlays and retain source credit without
suggesting Census endorsement.

As the [Census ZCTA guidance](https://www.census.gov/programs-surveys/geography/guidance/geo-areas/zctas.html)
explains, ZCTAs approximate address-based ZIP distributions using census blocks.
They do not represent every valid ZIP Code. Map labels must say **2020 Census
ZCTA**, and must not promise current USPS delivery coverage. This statistical
approximation is separate from cartographic vertex generalization.

Independent pin, source classification, API attribution, source currency,
overlay, and physical phone review remain held. This intake establishes neither
national geography completeness nor phone memory coverage. Original source
geometry and all historical prototype PDFs remain unchanged.
