# Geographic source snapshots

The national Geofabrik U.S. PBF snapshot is pinned by date, exact byte size and
computed SHA-256. Its full 12,238,337,062 bytes match the publisher's MD5 file.
`osmium fileinfo` identifies the replication timestamp as
`2026-10-29T21:21:26Z`. A SHA-256 pin protects subsequent fetches; publisher
checksum verification does not replace the required human pin review.

The file's header and the publisher's current U.S. extraction polygon do not
cover American Samoa, Guam or the Northern Mariana Islands. Do not interpret
“U.S. extract” as coverage of all territories. Comparing the publisher's
regional polygons with the pinned Census county geometries shows that the
Australia/Oceania parent polygon covers all three. The smaller extracts named
Samoa and Micronesia do not intersect those U.S. territory geometries.

Sources:

- [Geofabrik U.S. overview and dated snapshots](https://download.geofabrik.de/north-america/us.html)
- [U.S. extent polygon](https://download.geofabrik.de/north-america/us.poly)
- [Australia/Oceania overview](https://download.geofabrik.de/australia-oceania.html)
- [Australia/Oceania extent polygon](https://download.geofabrik.de/australia-oceania.poly)

Build territory-specific outputs from confirmed source coverage and Census
boundaries. Do not copy the whole regional extract into a territory's map or
directory, silently omit a territory, or treat a bounding-box check as a complete
road/reference audit. Full national orchestration and map measurements remain
unfinished.

The [2025 TIGER/Line technical documentation](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2025/TGRSHP2025_TechDoc.pdf),
section 1.2, permits reproduction of Census materials and asks that the Bureau
be cited. Section 1.1 explains the statistical boundary limits and the registered
TIGER/Line trademark. The catalog now cites that publisher evidence, and the
atlas and directory display the statistical-use and trademark notice.

The language-edition audit uses separate ACS inputs; see
[language-selection.md](language-selection.md). None of these source checks
approves clinical content, event-specific locations or emergency distribution.
