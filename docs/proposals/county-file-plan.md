# Complete county file planning

`ck.countyparts.plan_county_parts(data, evaluate, limits)` is a small prerequisite
for the existing county producer. It writes no files and starts no render jobs.
It accepts the existing projected `county`, `crs`, `zctas`, `zip_areas`, `roads`,
`settlements`, and `policy` fields. Geometry codes must exactly match the
relationship-derived county list. Use the authenticated, full-RI Census 2020
subset `census_zcta_ri_2020`; missing geometry is an error, never evidence that
the missing area has no ZCTA. Cross-county codes are clipped, not assigned to
only one county. ZCTAs remain dated Census approximations, not USPS boundaries.

The default is one complete county file. A split requires an intersecting
base-sheet guard failure or an explicit measured/predicted page/byte failure.
There is no population model or density-to-byte extrapolation. Unknown bytes
stay unknown. An actual bounded named-label factory can return
`page_limit_exceeded: true` with measured evidence and no invented page count.
Predicted values must be labeled and explained; they do not establish that a
PDF fits or that every street is labeled.

After a trigger, the planner considers clipped source ZIP areas and the entire
county remainder, including islands, water, and gaps. Oversized atoms are
bisected geographically within explicit depth/work limits. A deterministic
greedy pass merges neighboring entries in geographic order when their combined
budget permits. This is not an optimal minimum-file solver. The result checks
missing/extra/overlapping area and all supplied county-intersecting way IDs.
Unnamed ways remain explicit. Context ways outside the county are separately
reported; their absence from county ownership is not permission to omit visible
street context from actual sheets. Source locality names come only from supplied
settlement records. ZIP lists retain exact codes and never create min/max ranges.

## Integration contract

The root driver authenticates source and plan receipts, then adds `county`,
`crs`, `area_name`, and `plan_sha256` to each returned part's `id`, `geometry`,
and `zctas`. Pass that record to the producer's narrow `planned_part` hook after
county projection. Its geometry must be nonempty and inside the source county.
An explicit remainder part may have no ZIP codes. Its name must not imply that
the absence of a 2020 ZCTA means no postal service or no residents.

The producer builds base sheets for that geometry, reads only their union extent
from the authenticated Rhode Island road cache, and retains its actual source-way
guard. The existing page cap must count emitted intersecting sheets rather than
empty bounding-grid cells. For named-street preflight, run
`complete_detail_sheets(part_data, svg_map)`; report its actual page-limit failure
as measured evidence, preserving the diagnostic. Do not treat an unrelated
error or a depth-limit failure as a successful page measurement.

Render bounded parts into fresh attempt directories. Actual PDF pages/bytes can
replace unknown estimates. If an actual page/byte cap fails, preserve the failed
attempt and replan with that geometry's measured failure; do not adopt, relabel,
or silently truncate it. Reuse the cache and unchanged source inputs. The driver
must separately bound attempts, authenticate every final output, and prove the
final union covers the county and its supplied source ways before adoption.
Overview links may name only actual completed detail files. Neither this plan nor
an overview is a completed county map, source-extract audit, or handset test.

## Policy proposal, not new hidden defaults

Read existing map dimensions, scale, overlap, `max_pages`, and `pdf_max_bytes`
from the selected map policy/shared PDF configuration. Do not raise them here.
Record these additional required planner limits in the frozen run configuration:

| Field | Meaning |
| --- | --- |
| `max_parts` | Maximum proposed county files; failure retains all coverage |
| `max_depth` | Maximum bisection depth within each ZIP/remainder atom |
| `max_evaluations` | Maximum distinct geometry budget evaluations |
| `max_candidate_sheets` | Separate computational bound on grid cells inspected |
| `coverage_tolerance_m2` | Explicit geometric precision tolerance in projected metres |

The module supplies no numeric defaults for these new limits. Their engineering
values are configuration choices, not publisher facts. Tests use synthetic
limits and geometry; they make no Rhode Island population or performance claim.
