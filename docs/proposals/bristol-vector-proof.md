# Bristol County vector-map proof

The bounded county proof now has a geographic locator and nine atlas-scale
detail sheets in one PDF. It is a development component for the partial
Variant 1 preview, not an integrated sample or release. Original input files,
historical output pins, and the earlier diagnostic outputs remain unchanged.

The final diagnostic producer is source commit
`8ea18edea9905c7972bd094d1804440b350a28e8`, recipe
`county-vector-proof-v1-47a7ce6d611ad121e25fb3f1788380d99e51b13af95e98d077f599c4e4c18984`.
The original [evidence receipt](../evidence/bristol-vector-proof-2026-11-01.json)
records source-file hashes, inputs, actual exits, limits, layout, PDF structure,
and measured rendering results. Generated maps, SVGs, and PNGs are not in Git.

```text
3_MAPS_AND_PLACES/
  RI/
    Bristol County/
      0_OVERVIEW.pdf
      Bristol County 02806,02809,02885.pdf
```

| File | Bytes | Pages | SHA-256 |
| --- | ---: | ---: | --- |
| `0_OVERVIEW.pdf` | 432,229 | 3 | `37adbf4bef49bb1095e40e7e512683f32b602af5af57057c0092812c0274bd70` |
| `Bristol County 02806,02809,02885.pdf` | 799,367 | 10 | `043f833a406865f6babb8d03b9b32e736e96d3b7e531b0db90f91fd6abfcbee8` |

The initial trial uses 1:25,000 detail, a 190 × 230 mm map frame, and 10% sheet
overlap. These are measured engineering-trial inputs, not publisher defaults or
final national settings. The byte limit comes from the integrator's frozen
`config/build.yaml`, whose exact hash is retained in the receipt. The county
fits that provisional 10 MB guardrail, so no locality files were needed.

Roads and names come from the pinned RI OSM extract. Water geometry comes from
the existing, verified RI PMTiles derivative, preserving its historical recipe
and seed binding. Only allowlisted water geometry enters the map; hidden POI and
infrastructure tile layers do not. The overview retains all 33 Bristol records
from the historical directory, whose `complete:false` status is disclosed and
unchanged. The Census 2020 ZIP-area relationship input is registered as a held,
build-only catalog record; its three codes are not a current USPS coverage claim.

Inline SVG and the existing WeasyPrint stack preserve vector roads and text.
All 13 PDF pages have zero image XObjects, and all 178 placed road-name labels
are extractable. Nine sheet bookmarks and continuation page references match
the actual PDF pages 2–10. Creation and modification dates match the development
epoch, 2026-10-31 UTC. No clean repeat pair has been run.

The first geographic-locator iteration visibly clipped a redundant Position
column. The corrected version removes it and bounds the Sheet/Page table beside
the locator. The producer now inspects actual WeasyPrint table, cell, and SVG
layout boxes before PDF output; all 449 inspected boxes fit their pages. Off-page
table/SVG fixtures exercise that guard. Eight focused tests pass with the
authoritative font cache and no skips; Ruff and formatting pass.

The corrected proof ran offline on the pinned build image with one CPU and a
2 GiB memory-plus-swap cap. It exited 0, took 143.51 seconds in the producer,
and peaked at 1,231,007,744 bytes of cgroup memory without memory-limit or OOM
events. A separate 512 MiB Linux PDF inspection rendered the cover at 780 pixels
wide in 0.239 seconds and the critical detail at 390/1170 pixels in 0.234/0.578
seconds. That inspection peaked at 133,873,664 bytes. These are Linux proxy
measurements, not handset latency or a 95% phone-coverage result.

Local inspectable assets are under
`.worktrees/107-bristol-vector/build/bristol-vector-locator-v3/`.
The corrected cover and fit/zoom PNGs are under
`.worktrees/107-bristol-vector/build/bristol-visual-locator-v3/`.
The geographic cover and zoomed detail were visually inspected. Dense overview
marker labels still overlap in places; every source record remains in its index.
Physical phone/USB checks, full RI coverage, source/rights reviews, and release
acceptance remain open. No national run or image-verifier development was added.
