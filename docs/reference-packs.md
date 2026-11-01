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

## Earlier development repeats

At development epoch 1793404800, separate network-disabled Linux containers
produced identical PDF payloads and complete generation manifests for:

| Pack | Articles | Placed bytes | Canonical generation SHA-256 |
| --- | ---: | ---: | --- |
| Automobile maintenance | 6 | 237,774 | 9dfd807496607328b1a7c13ed963445c4c70dc4c5419ff53835dc6fa393fa500 |
| Carpentry and hand tools | 7 | 188,024 | 5ad485a9ea805fed9cf79e35038c52bd905b485f9d5dca2d51258482954bc043 |
| Electronics background | 9 | 455,499 | c94e7cd216290d4f2599ece06a2d4b33e6e1832e3063d4426eac283308b7e866 |

These two selections contain 134 phone pages in total. Two rendered pages were
visually inspected for layout; this is not a physical phone or technical review.
These checkpoints predate the equation renderer below. They do not clear the
source-currency, safety, suitability or final release-epoch gates.

The later source-character and markup checks found a missing penguin character
and MathML equations that the installed PDF renderer did not lay out natively.
The reference font settings now include the pinned monochrome Noto Emoji font
under OFL-1.1. Source characters are retained.

The shared reference converter now uses the pinned MathJax full package to
render original MathML as vector SVG, including fractions, accents and script
positions. Bun runs the original publisher package offline, directly; no package
install, source modification or runtime network access is needed. The tarball's
published SHA-512 integrity was checked, and its SHA-256 and license proof are
recorded in `catalog/buildtools.yaml`. The package is a build input and is never
placed on a drive. Generated SVG must contain vector geometry without scripts,
external resources, fallback text glyphs or renderer errors. Source figures
remain unavailable; regenerated equations are identified separately in audits.

A preflight of all 29 selected articles rendered 36 source equations with complete
body-font coverage. A separate scan found 29 MathML equations across five
existing medical PDFs: ectopic pregnancy, altitude sickness, sterilization,
hypoxia and pulse oximetry. Medical references and phrasebooks use the same
verified converter. Their generation pins are reset until complete independent
repeats match. Named clinical and source review remains required.

Each equation audit records a hash of the parsed source MathML and the generated
SVG. Source article byte hashes and revision links remain intact. The pipeline
binds the MathJax package, Bun version, source files, settings and renderer script
in its provenance. Vector equations support zoom without raster degradation;
physical readability and source-to-PDF comparison remain review tasks. The
original medical instructions and numeric values have not been rewritten.

## Equation-preserving development repeats

At the same development epoch, all four packs completed independent builds in
network-disabled Linux containers using the pinned MathJax recipe. Complete
generation records matched. The canonical copy and both independent outputs
were then checked against every recorded payload and intermediate hash.

| Pack | Articles | Placed bytes | Canonical generation SHA-256 |
| --- | ---: | ---: | --- |
| Automobile maintenance | 6 | 249,547 | 5ded659a2268b95d9589ddbbd97b2f9d945263442046a73fd1b3c7208dda0e30 |
| Carpentry and hand tools | 7 | 199,797 | 20c1eb14ca235943efa2f53c9f11fc9cb9e0b5013d6b59ee53622dfbd7699b3b |
| Electronics background | 9 | 509,136 | a6a89725b5f83f97d4f94a8a11844f97d8b67fb4b0f149dfd713ade57280716e |
| Physiology background | 7 | 1,188,529 | 33e4c9b3ec056f4bd1b31616e49e6cfe5398e70ab1b8e6b206315d94dd9fd512 |

Recipe: `reference-pack-v1-4baab6635d5504539909a0d1054ea0d68ce2b9d09fdeb378cb35b456a3b4fb67`.
A rendered electronics page was visually checked for fraction and exponent
placement. This does not establish source accuracy, clinical suitability or
physical phone legibility. All named review gates remain open.
