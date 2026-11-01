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

`ck national-points --cache cache --output build/national-points --epoch EPOCH`
imports the shared federal files and the configured U.S., Oceania, Puerto Rico
and U.S. Virgin Islands OSM extracts once. Parent selection is shared with
Android maps in `pipelines/androidmaps/national.yaml`.
It assigns points to Census counties, deduplicates exact source identifiers,
and writes a bound `places.json` intermediate for all state atlas jobs. Pin
its measured generation manifest as `directory_points` before using it.
State directory builds can reuse it with `--points build/national-points
--points-id directory_points`; they still require the matching final atlas
index to publish page and grid references.

Invalid or incomplete OSM area geometry is recorded with its source identifier
and omitted from the mapped points. No replacement location is inferred.
Published missing FCC coordinates and absent FEMA county profiles also remain
in the audit and public source data. A finished import can be complete with
these disclosed publisher omissions; completeness does not mean exhaustive
coverage or approve the catalog pins. Final directories still require every
included place to have a checked atlas reference.

The pinned NCES EDGE location workbook does not include school grade levels.
Entries are labeled public schools; their names are not used to infer elementary
school status. The rally rule remains the configured public elementary school
rule. A future verified grade-level join can improve the directory.

The [2025 TIGER/Line technical documentation](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2025/TGRSHP2025_TechDoc.pdf),
section 1.2, permits reproduction of Census materials and asks that the Bureau
be cited. Section 1.1 explains the statistical boundary limits and the registered
TIGER/Line trademark. The catalog now cites that publisher evidence, and the
atlas and directory display the statistical-use and trademark notice.

The language-edition audit uses separate ACS inputs; see
[language-selection.md](language-selection.md). None of these source checks
approves clinical content, event-specific locations or emergency distribution.

The first national point import mapped 254,062 places across all 3,235 Census
county geometries and 56 jurisdictions. The source-omission audit contains 19
FCC geographic exceptions and two invalid OSM areas. FEMA lacks profiles for
`60030`, `60040` and `69085` in this snapshot. American Samoa, Guam, the Northern
Mariana Islands, Puerto Rico and the U.S. Virgin Islands all have mapped places.
These are measured build results, not claims that any place is open or that the
directory is exhaustive. See [national-atlas.md](national-atlas.md) for the
remaining atlas stages.

Two independent runs of that first point-data recipe matched the public
payload, bound point intermediate and generation manifest. Subsequent state
extraction exposed that Puerto Rico and the Virgin Islands had federal points
but zero OSM places. That source-selection gap invalidates the earlier corpus
as a release candidate despite its repeatability. The active point pin is
unconfirmed until the corrected import passes jurisdiction/source coverage
checks. See [territory-source-coverage.md](territory-source-coverage.md).
Descendant atlases, directories, Android maps and full images need corrected
inputs and their own complete repeated builds.
