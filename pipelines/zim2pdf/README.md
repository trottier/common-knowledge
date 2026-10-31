# Medical reference conversion

`ck medpdf --output build/medpdf/medical_phone_pdfs --epoch <fixed-epoch> --jobs 3`
reads the draft selection in `catalog/medpdf_topics.yaml`. Run it in the pinned
Linux amd64 build container with the repository cache mounted and networking off.
`--limit N` creates an explicitly incomplete development subset. Outputs must go
to a new directory. Fonts and archives are fetched by reference, never committed.

The initial selection contains 150 English WikiMed articles. A clinician must
review the selection and conversions before release. WikEM's own
[license page](https://wikem.org/wiki/Creative_Commons) confirms CC BY-SA 4.0, but
an exact currently available publisher ZIM has not been found in the Kiwix
catalog or archive. Its catalog entry remains unresolved. Do not substitute an
unverified third-party copy.

## Source validation

Every input is checked against its catalog size and SHA-256. `zimcheck --all
--json` must finish every required check. The downloaded October 2026 WikiMed
archive matches the publisher's metalink SHA-256, but the current checker reports
three malformed internal links in `Clavicular_notch`, `Hindered_phenol` and
`Woodlands_Hospital_(Darlington,_United_Kingdom)`. These failures block placement
of the publisher archive. Its byte-identical input is
kept in the ignored `cache/quarantine/<sha256>` directory.

Only regeneration inputs may allow explicitly repairable content-link errors.
Internal links need a separate allowance; shipped archives always use the strict
audit. Checksum, integrity, redirect and all other structural errors still fail.
Structural checks and both link phases run separately so a failing phase cannot
mask a later error. The complete audit is retained in `archive-audits.json` and
bound into the generation manifest. This exception never applies to shipped
ZIMs: fetch and assembly use the strict audit. Failed format checks retain
checksum-verified downloads in quarantine so retrying does not download them
again.

The build installs the catalog-pinned static `zimcheck` 3.8.0. Debian Bookworm's
older checker cannot validate the newer writer's title-index format reliably.
Unexpected checker diagnostics fail closed even when the JSON also lists known
external dependencies.

The old 3.1.3 checker also reported two external resources inside inactive source
metadata. Direct HTML inspection and the current external-resource audit confirmed
those were false positives. Those articles are not changed by the archive rebuild.

The pipeline uses [libzim's reader API](https://python-libzim.readthedocs.io/en/latest/api_reference/libzim.reader/)
and [zimcheck](https://github.com/openzim/zim-tools/tree/3.8.0/src/zimcheck).
It follows archive redirects and requires the publisher's per-article revision
date, revision URL and matching CC BY-SA license notice. Missing provenance
fails conversion. Original HTML hashes and actual resolved entry paths are
recorded in `articles.json`.

## Offline adaptation

Article prose, table cells, source numbers and references are retained. Tables
are reflowed into labeled rows and columns, with row and column spans stated
explicitly. This lets long cells continue onto another phone page. The pipeline
checks that every source table text node survives. Site
navigation, edit controls, scripts, forms, styles and embedded resources are
removed. Unavailable source figures are replaced with a notice that preserves
their alternative text; the article text license is not treated as permission
for separately licensed media. Relative links to unshipped articles are removed
while their words remain. Internal article links and HTTPS reference links stay
clickable; rendering performs no network requests.

Each phone PDF has 90 × 160 mm pages, 12 pt base type, a linked contents list,
heading bookmarks, source attribution, edit date and license. Development copies
carry a draft footer. Font glyph coverage and page bounds are checked
before writing the PDF. These checks do not replace clinical or phone review.
The conversion uses only checksum-verified catalog fonts, including the scripts
present in source citations.

Rendering uses a fixed epoch, stable font resource aliases, tagged PDF output
and a deterministic identifier. Worker count does not determine file ordering.
The manifest records every payload hash, tool versions, input pins and the
pipeline fingerprint. Build audit HTML is retained outside the placed payload.
Generation completeness records processing of the whole selection; the catalog
and release gate independently require named human medical review.

## Reader

`kiwix_android` pins the publisher's universal standalone APK, its published
SHA-256, verified signing certificate and exact source commit. The source archive
is a candidate corresponding-source bundle. Dependency closure, pin review and
physical offline-reader checks remain explicit blockers. Windows, Linux and Mac
readers also have measured download pins, matched publisher MD5 files and exact
source candidates. Their dependency-source closure and device tests remain open.

## Rebuilt archive

`ck offline-zim --item wikimed_en_nopic --output build/zim-offline/wiki --epoch
<fixed-epoch>` regenerates an archive from the source data. Only entries named
by the content-link audit are adapted. Broken link targets are removed while
their visible words remain; external embeds, if found, are replaced with notices.
Article attribution and revision notices remain. Every
other user entry's bytes, MIME type, title and redirect target are compared with
the publisher archive after rebuilding. The publisher file stays untouched.

The rebuild uses a single compression worker and normalizes identifiers in the
generated ZIM header and generated Xapian Glass title index. It then recalculates
the ZIM format's internal MD5 and runs every checker test again. SHA-256 remains
the catalog integrity pin. Header positions and Glass UUID layout follow the
[libzim header implementation](https://github.com/openzim/libzim/blob/main/src/fileheader.cpp)
and [Xapian Glass implementation](https://github.com/xapian/xapian/blob/RELEASE/1.4/xapian-core/backends/glass/glass_version.cc).
A small fixture checks byte-identical rebuilds and strict offline validation.

Title search is retained. The publisher's original full-text index is omitted in
this regenerated edition; this limitation is written into its placed `SOURCE.TXT`.
The full-archive prototype passed every format check and the entry comparison.
Its measured payload is 753,161,199 bytes, including `SOURCE.TXT`. The catalog pins
that generated manifest while repeat full-archive reproducibility, pin review and
physical reader checks remain open. The original source is a build input only.

All 150 phone PDFs and their README matched byte-for-byte across two complete
builds with different worker counts (69,194,073 payload bytes). The first pair's
audit manifests exposed nondeterministic duplicate-content warning pairs from the
checker. The audit now records sorted duplicate equivalence groups, retaining all
errors and the complete set of affected paths. Clean runs with this correction are
in progress; the earlier payload match alone is not a whole-manifest match.
