# Bristol places companion proof

The existing overview has the 33 numbered names and available addresses, but
its 9 pt table omits coordinates and detail-map page/grid references. It also
splits one school entry across pages. This companion reuses those exact 33
records in a 90×160 mm, 12 pt phone layout through the existing directory renderer.
It adds no source records or live availability claims. The broadcast reference
retains its warning that public access is not implied.

`tools/build_county_places.py` authenticates the existing 124 map proof and its
original historical RI directory generation, source payload, and intermediate
records. It validates the county records through the existing Place/exclusion
policy and retains the overview's exact 1–33 order. References use current
projected sheet bounds, printed A–E/1–6 grid, actual leaf filename, and checked
PDF page/sheet headings. Overlap chooses the sheet where the point lies farther
from an edge; no old statewide atlas page number is reused.

The B packet contains the draft PDF, a documented county-only source offer with
its original fields and dates, and the ODbL notice. The authenticated whole-state
source stays outside the drive. All other counties and county profiles are
excluded from this source offer. A was an earlier unadopted proof with a
whole-state source copy; it remains historical evidence and is not relabeled.

Every page says “May help; not confirmed open.” in ordinary readable type.
Dates and process notes use 8 pt fine print. All 33 names, coordinates, and actual
page/grid references pass extraction checks; the opening, first places, and
last place/source notes render clearly in desktop Chrome at 390 px. These checks
are not physical-phone acceptance or human source/safety approval.

The output remains a separate proof. Root-coordinated adoption must preserve
its source offer/notices and regenerate actual-tree map and copy indexes: the
existing map-finder inventory covers two county PDFs, and the companion adds a
third. [Evidence](../evidence/bristol-places-companion-2026-11-01.json) records
actual input, recipe, output, and visual-check hashes.
