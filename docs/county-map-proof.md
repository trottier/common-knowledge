# County map development proof

The current experiment covers Bristol County, Rhode Island. It keeps one
detailed, multipage PDF per county, with a separate overview:

```text
3_MAPS_AND_PLACES/
  RI/
    Bristol County/
      0_OVERVIEW.pdf
      Bristol County 02806,02809,02885.pdf
```

The detailed PDF contains a geographic sheet locator, clickable page references,
overlapping road sheets, continuation references, coordinates, a grid, a scale
bar, and vector roads and text. The Bristol trial starts with nine base sheets
and adds larger-scale street sheets as needed inside the same county PDF. The
number of insets is an output of coverage checks, not a fixed page count. Each
inset records its effective scale, parent sheet, and return reference; an index
links to the enlarged sheets.

Every street named in the selected source must be labeled, including local
streets. Short OSM segments and collisions cannot silently remove names. The
coverage target uses all named source-way IDs and their associated names, so
disconnected streets sharing a name still require coverage. Unresolved coverage,
page limits, or the configured per-file byte cap fail the build. Source roads
without names remain explicitly unnamed; no street names are invented.

The overview carries historical public-place markers and an index, plus verified
ZIP-area polygons and code labels. The code list comes from the pinned Census
2020 ZCTA/county relationship file, and the plotted areas use pinned Census
geometry checked against those codes. Filename codes alone are insufficient.
These 2020 Census geographic approximations are not a current USPS delivery
directory. The three verified codes are distinct, so the filename keeps their
gaps rather than inventing a continuous range.

The trial scale, overlap, and resource guards live in
`pipelines/atlas/bristol-proof.json`. The per-file byte guard comes only from
`pdf.max_file_mb` in `config/build.yaml`, currently 10 decimal MB. Read that
configuration value instead of repeating the limit in generators. Neither this
trial scale nor its Linux rendering measurements establish suitability for every
county or phone.

Run the tool inside the pinned build environment, with the verified cache and
prepared inputs mounted read-only. Select a new, empty output path:

```sh
rtk proxy uv run python tools/prototype_county_map.py \
  --root . \
  --cache /cache \
  --basemap /prepared-rhode-island-basemap \
  --points /prepared-rhode-island-directory \
  --zip-source /cache/3ed41278d637dc249e0323306f68be8a6c234e3090f4de88ef328dee71aeaaaf \
  --pdf-budget-config config/build.yaml \
  --output build/new-county-proof
```

The producer verifies the selected input files and historical manifests before
rendering. It preserves the historical directory's incomplete status, rejects
county coverage gaps, checks actual page references and bookmarks, and rejects
off-page tables or SVG map frames. Tests also cover named-way association,
short and segmented local streets, disconnected equal-name roads, unnamed roads,
inset limits, and ZIP-area geometry. Inspect the actual map labels and scale
bars: a street name found only in an index or heading does not establish that
the map labels it. `prototype.json` records input hashes,
producer files, policy, output sizes, hashes, and measured resource use.

The first all-street render (A) is held because its fixed scale bar did not
remain within the reserved space on enlarged sheets. It is historical evidence,
not a final artifact. The corrected B repeat is pending; its actual PDFs,
coverage, pagination, scale bars, and byte limits must pass inspection before
adoption. No final B measurements are claimed here.

This is an unreviewed development proof, not a complete sample or a new national
atlas pin. Its historical directory has 33 county entries; that does not
establish complete current public-place coverage. Neighboring-state navigation,
physical-phone memory and interaction, and clean-build reproducibility remain
unproven. Diagnostic layout iterations are not reproducibility pairs.

Copy only the inspected PDFs into an explicitly incomplete development tree,
retain their exact provenance outside that tree, and inspect the real files with
`ck explore`. Do not give historical artifacts the current checkout's producer
identity or replace an existing image's manifest with a preview inventory.
