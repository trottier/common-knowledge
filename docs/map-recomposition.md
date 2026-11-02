# Recompose the cached Bristol maps

`tools/recompose_county_map.py --root ROOT --prepared PREPARED --output OUTPUT`
changes document typography and surrounding text using the existing vector maps.
It calls `ck.map_recompose.recompose(root, prepared, output)`. It never reads the
PBF, PMTiles, or original directory database, replans sheets, or places labels.
Use a fresh output directory; an existing output is rejected.

`pipelines/atlas/bristol-recompose.json` pins the original final B prototype
receipt and its source commit, `39868af6712d6d4d591fc29e9f516d2e36d255c7`.
Before writing output, the pipeline verifies the original PDF hashes and sizes,
checks that each first PDF identifier is the ASCII SHA-256 of its cached original
HTML, and requires each cached SVG to be an exact, unique substring of that
HTML. It checks the named source-way inventory, actual SVG names, and pinned
font bytes. The unchanged public-place rows are recovered from the authenticated
overview table, because the historical receipt records their IDs but not their
names and addresses.

The new template keeps map instructions, street-sheet navigation, and public
places prominent. Publication, incomplete-source, review, and boundary caveats
occupy a separate 8pt source-note section. Required source dates, attribution,
and the public-place opening caveat stay in fine print. The footer says
“Preview · page N.” No review status or source completeness is promoted.

The new receipt preserves the original producer and receipt hash, cached HTML
and SVG hashes, original input pins, missing-way inventory, incomplete parent,
and source epoch. Its new recipe binds the recomposition code, template, source
pin, shared PDF budget, fonts, environment inputs, and library versions. Newly
rendered PDF hashes are recorded separately. Actual sheet bookmark destinations,
horizontal layout, page limits, and the configured per-file byte budget must
pass before a final receipt is written. A failed output without a final receipt
is a diagnostic, not an adopted artifact.

Run inside the existing pinned build image, with source, prepared proof, and
font cache mounted read-only, networking disabled, and only a fresh output
parent writable. The prepared input is the original
`.worktrees/117-map-readability-integration/build/bristol-streets-zip-b` directory;
no basemap, PBF, or places mounts are needed. Keep the updated full county PDFs
local while selecting a few representative inspection pages separately. This
recomposition does not establish an independent repeat or physical-phone result.

For a tiny hosted example, run `tools/prepare_mobile_examples.py` inside the
same pinned container with `--prepared` pointing to the recomposed map output,
`--prototype-sha256` set to the actual `prototype.json` hash, `--cache /cache`,
`--output` a fresh examples directory, and `--receipt` a new external JSON path.
Keep source and cache mounts read-only and networking disabled. The helper
renders the overview's first section and street sheets I04 and I24 from the
authenticated cached HTML/vectors. Fonts are verified and subset only for these
pages; extracting PDF pages directly can retain the full atlas's shared
resources. Samples retain attribution, the ZIP approximation caveat, original
atlas page numbers, and a note that continuations are in the full atlas. Links
to omitted pages are removed. The full county files remain unchanged locally.

Export that small folder with `ck export-preview` for hosting. Do not deploy the
full local Variant 1 tree or the build receipts. The examples are unreviewed
development files and do not establish complete coverage or phone acceptance.
