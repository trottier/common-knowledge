# WikEM publisher API source edition

No exact downloadable WikEM ZIM pin has been confirmed. The project can instead
regenerate a text archive from exact public publisher API revisions. The
[publisher license page](https://wikem.org/wiki/Creative_Commons) states CC BY-SA
4.0. Its captured evidence is a required source input. This does not approve
individual computed source pins or replace the release's human reviews.

`tools/snapshot_wikem.py` first captures the complete namespace-zero page listing,
then revision metadata and publisher-rendered HTML at the selected revision IDs.
Publisher translation suffixes come from `pipelines/wikem/settings.yaml`; they
are separate from the project's fifteen edition choices. The initial listing
contained 4,285 English article candidates and 6,641 English redirects. The
completed acquisition encountered seven restricted hospital pages. The
publisher denied their content; those pages are excluded and the observations
are recorded. The accepted public set has 4,278 articles and 6,641 redirects.
Its 4,655 publisher response records total 121,395,005 input bytes.

```sh
python3.12 tools/snapshot_wikem.py \
  --listings build/wikem/listings --output build/wikem/snapshot \
  --cache cache --captured-on YYYY-MM-DD
```

The tool waits at least one second between fresh requests and supplies MediaWiki's
`maxlag` parameter. It resumes only responses whose original request URL and
exact bytes still match their saved record. A publisher access denial removes
only the named page and records the error response's SHA-256 and request URL.
An ambiguous denial stops the acquisition. The tool does not log in or try
another endpoint to retrieve denied content. HTTP errors, hidden revisions and
unexpected source IDs are never accepted as article content.

The output is a proposed catalog plus a separate scope-exclusion record. Review
and install the scope record in `config/wikem-scope.yaml` and the external input
entries in `catalog/`. Captured JSON and HTML stay in the ignored cache. Each
accepted response has its own publisher URL, exact size, SHA-256, license proof
and attribution. Exact immutable preservation and independent pin/scope review
remain release gates. Refreshing source data requires a new acquisition folder,
not overwriting an existing snapshot.

After the accepted input entries are fetched:

```sh
ck wikem --cache cache --output build/generated/wikem_en_nopic \
  --epoch "$SOURCE_DATE_EPOCH"
```

The builder requires complete listing pagination, every selected public revision
and every corresponding article response. Exclusions must name pages in that
listing. It preserves article tables and spans, retains formula text, replaces
figures with visible omission notices and disables interactive widgets. It
removes scripts, automatic remote resources and event attributes. Internal links
resolve against the captured title set; unavailable targets retain their visible
words. Redirect titles get a visible source redirect and an available offline
link. The original publisher downloads are unchanged.

Every article records its exact original revision, edit date, source link and
CC BY-SA attribution. The ZIM includes a title index, a static article index and
an original generated book icon; it has no full-text index. UUIDs and search
index IDs derive from fixed inputs. `zimcheck` must pass, and a bound audit
records figures, disabled controls, unavailable links and scope exclusions.

Two independent complete archive builds pass strict `zimcheck` and have
identical payloads and generation manifests at development epoch 1793404800.
The measured payload is 8,601,054 bytes; its generation manifest SHA-256 is
`e12d046fa48c16f7aa9a5cab8bfc6de2c142f62fc195820d26fab7d64fddcdd2`.
The source capture, public-page scope and output pins are recorded in the
catalog. Pin/scope review, immutable source preservation, clinical review and
physical reader checks remain open. A complete build is not release approval.

The real source set includes four `#REDIRECT:` revisions. The redirect parser
accepts the optional colon and preserves the target and section fragment.
All 6,641 captured redirect revisions parse. Regression fixtures cover both
publisher forms; an unsupported form still fails instead of dropping a title.

The larger API catalog uses a bounded parser cache keyed by actual file bytes.
Callers receive independent catalog models; a test also changes a same-sized
file while preserving its timestamp to verify that changed inputs are observed.
This keeps repeated PDF rendering from reparsing thousands of unchanged source
pins without hiding source edits.

The complete actual-payload cleanup audit covered all 4,278 captured articles
and 2,759 tables and found no lost table words. This automated text check does
not establish clinical correctness. The focused WikEM, catalog and medical-PDF
checks pass 56 tests, including optional redirect colons, combined archive
licenses and canonical-title selection.

The medical PDF pipeline can also read a catalog-pinned generated ZIM from
`--generated build/generated`. It requires one complete archive at the requested
epoch, checks every input and payload hash, and runs strict ZIM checks. Selecting
an alias page as a medical article fails with a request for its canonical title.
A medical selection cannot claim review without a named reviewer and ISO date.
The selection remains a draft: 150 WikiMed topics plus eight canonical WikEM
topics. Its first complete 158-article phone pack at the common development
epoch measures 69,972,654 bytes, with generation manifest SHA-256
`b5230956e245e6354661df08fbb6899f6f95acff6ad23fa190c4ceef6343723c`.
An independent complete repeat produced identical bytes for every output file,
including the complete generation manifest. No selection or clinical review
status has been changed to reviewed.
