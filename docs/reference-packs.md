# Selected reference phone PDFs

`ck reference-pack --pack reference_howto_1 --cache cache --output build/reference-h1 --epoch 1793404800`
regenerates the exact articles named in `pipelines/referencepacks/selection.yaml`
from the pinned English Wikibooks ZIM. The four initial selections contain 29
articles in total: six automobile maintenance articles, seven carpentry articles,
nine electronics articles and seven physiology articles. They populate the two
how-to collections, repair and medical in-depth knowledge, respectively.

These are draft background references. They have not been approved as emergency
procedures or complete illustrated manuals. The nopic source omits figures,
which can remove essential information, especially for electronics and anatomy.
Each PDF and the collection README state that limitation and direct readers to
START and the printed cards. Selection, safety, accuracy, suitability and device
readability review remain catalog gates. The agent never grants review status.
The physiology selection is supplementary to the universal medical references;
it is not a replacement for the existing 158-article emergency selection.

The pipeline verifies the raw archive's byte hash and structural/content audit,
then rejects source redirects, disambiguation pages, non-HTML entries and missing
or mismatched revision/license notices. The shared article converter preserves
source prose, numbers, table cells and revision attribution, reflows tables,
removes active resources and labels unavailable figures. Source downloads are
never changed. PDF fetching is restricted to pinned font aliases, and missing
font glyphs or clipped text fail the build.

Output uses numbered FAT-safe names, phone page dimensions, at least the shared
12-point base type, heading bookmarks and a contents page. Exact article paths,
source HTML hashes, revision dates, omissions and PDF page counts are retained
in the generation audit. Temporary output is published only after every article
succeeds. Complete generation metadata binds the source, fonts, selection,
converter, templates and container recipe. Separate clean runs must match before
measured development pins replace the catalog markers.

`make full` prepares the four packs through the ordinary input dependency graph.
No imported source files, fonts, ZIMs or PDFs are committed to git.

## Measured development repeats

At development epoch 1793404800, separate network-disabled Linux containers
produced identical PDF payloads and complete generation manifests for:

| Pack | Articles | Placed bytes | Canonical generation SHA-256 |
| --- | ---: | ---: | --- |
| Automobile maintenance | 6 | 237,774 | 9dfd807496607328b1a7c13ed963445c4c70dc4c5419ff53835dc6fa393fa500 |
| Carpentry and hand tools | 7 | 188,024 | 5ad485a9ea805fed9cf79e35038c52bd905b485f9d5dca2d51258482954bc043 |

These two selections contain 134 phone pages in total. Two rendered pages were
visually inspected for layout; this is not a physical phone or technical review.
The electronics and physiology pairs are still running. These checkpoints do
not clear the source-currency, safety, suitability or final release-epoch gates.
