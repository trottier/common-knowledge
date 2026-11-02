# Bristol County streets and ZIP-area proof

A frozen Bristol County proof now supplies the actual map files in the incomplete
Variant 1 sample preview. It labels every named source way observed in the bounded
map extent and shows the three verified 2020 Census ZCTA polygons. This is a
usable inspection artifact, not a complete Rhode Island sample or a release.

[The evidence receipt](../evidence/street-zip-map-proof-2026-11-01.json) records the
exact inputs, producer, output hashes, original browser report, resource results,
and retained limitations. The frozen map source is
[`39868af6712d6d4d591fc29e9f516d2e36d255c7`](https://github.com/trottier/common-knowledge/tree/39868af6712d6d4d591fc29e9f516d2e36d255c7).
No producer files, PDFs, source cargo, fonts, screenshots, or web application code
change in this evidence packet.

## Actual files and checks

```text
3_MAPS_AND_PLACES/RI/Bristol County/
    0_OVERVIEW.pdf
    Bristol County 02806,02809,02885.pdf
```

| File | Pages | Bytes |
| --- | ---: | ---: |
| Overview | 3 | 466,979 |
| Detailed county maps | 46 | 6,371,165 |

Both files fit the configured provisional 10,000,000-byte limit. The detail PDF
contains a locator, nine base sheets, 34 enlarged street sheets, and a two-page
inset index. All 43 map bookmarks resolve to their recorded pages, 2–44; the index
occupies pages 45–46. PDF creation and modification dates match the map epoch
`1793404800`, October 31, 2026 UTC.

Coverage checks found no omitted expected ways among 2,344 named source ways.
All 1,510 distinct source names occur in actual map SVG text nodes and in the
actual detailed PDF text. These are checks against pinned source data, not a
claim that every real-world road has a supplied name or that every route is open.

The first diagnostic, A, remains held because its fixed 500 m scale bar could
exceed the reserved inset space. Final B uses a bounded 1/2/5 distance selection.
An independent audit checked all 44 actual SVG scale paths, including the
overview: each fits 40 mm, and each detail bar agrees with its recorded distance
and map extent. A rendered depth-two inset, I15 on page 25, visibly shows its
correctly contained 200 m bar. A and B use different recipes; they are not a
reproducibility pair.

## Actual visual and browser evidence

The final B files were rehashed and copied byte-identically into
`build/current-builds/variant-1-preview-v3`. The saved native desktop Chrome
report records actual folder navigation, the complete ZIP filename at 390 CSS
pixels, ZIP search, the 46-page detail PDF, the three-page overview, and returning
to Rhode Island. It reports no browser errors or external HTTP requests.

The final B browser screenshot visibly shows Woburn Street on page 14, sheet I04,
at six times fit. The overview screenshot shows the distinct outlines and labels
`02806`, `02809`, and `02885`. Sloop Lane is visibly readable in the diagnostic A
PDF crop on page 34, sheet I24. Final B preserves every A street-label placement,
sheet bound, and page, so that crop is supporting layout evidence; it is not
represented as a separate final B browser inspection. Screenshot paths and hashes
are bound in the receipt, while the original binaries remain outside git.

Whole-document text alone cannot prove that a name appears in the map rather
than an inset header or index. Cropped Poppler layout extraction split or
reordered rotated names; an attempted positional pypdf visitor sometimes returned
SVG-local coordinates through nested forms. Those attempts were not accepted as
map-region absence evidence. The retained support is actual SVG text, whole-PDF
text, empty source-way omissions, unchanged placements, and inspected map regions.

## Resources and remaining holds

Final B took 175.18 seconds in the pinned existing container with one CPU, a 4 GiB
memory cap, read-only source/cache mounts, and networking disabled. Peak RSS was
941,688 KiB; actual cgroup memory peak was 1,064,169,472 bytes, with no OOM events.
The independent read-only decoder audit used one CPU and a 512 MiB cap, peaking
at 217,960,448 bytes without OOM events. These are build and desktop inspection
measurements, not handset memory measurements.

All 33 historical Bristol public-place points remain present. Their parent
directory stays `complete: false`, and its provenance is preserved. The ZCTAs are
2020 Census statistical approximations, not current USPS delivery boundaries.
The partial preview contains English core and maps with different component
epochs; it is not a single-epoch image. Named human review, physical phone and USB
tests, a clean same-recipe repeat, complete sample cargo, and release checks remain.
The 95% phone-coverage goal is not established by these files or desktop previews.
