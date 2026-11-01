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
contains 4,285 English article candidates and 6,641 English redirects. The
ongoing acquisition has encountered seven restricted hospital pages. The
publisher denied their content; those pages are excluded and the observations
are recorded. Final public counts remain provisional until acquisition completes.

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

The small container fixture produces identical archive bytes in fresh runs,
including title search and redirect navigation. Tests preserve tables and
formula text, reject incomplete listing chains and verify every source revision.
These are pipeline checks, not a completed national source capture, medical
content review or physical Kiwix reader test. The complete WikEM item remains
unconfirmed until the full public source set builds, audits and repeats.

The larger API catalog uses a bounded parser cache keyed by actual file bytes.
Callers receive independent catalog models; a test also changes a same-sized
file while preserving its timestamp to verify that changed inputs are observed.
This keeps repeated PDF rendering from reparsing thousands of unchanged source
pins without hiding source edits.

A preliminary actual-payload audit covered 1,044 captured articles containing
818 tables and found no lost table words after cleanup. The complete implementation passes
223 container tests, including generated-archive source checks for the medical
PDF reader; the focused WikEM, catalog and medical-PDF checks pass 56 tests. Full captured-archive builds and repeated hashes remain pending.

The medical PDF pipeline can also read a catalog-pinned generated ZIM from
`--generated build/generated`. It requires one complete archive at the requested
epoch, checks every input and payload hash, and runs strict ZIM checks. Selecting
an alias page as a medical article fails with a request for its canonical title.
A medical selection cannot claim review without a named reviewer and ISO date.
The existing 150-article selection remains a draft; adding WikEM topics waits
for the complete source archive and its measured catalog pin.
