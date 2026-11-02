# Cached medical reference framing

The medical reference templates keep a clear “Unreviewed medical reference” notice
and practical START/printed-card instructions in ordinary text. Publication dates,
archive versions, adaptation details, and source/license links occupy a separate
8pt source-note area. Generated missing-figure markers and table-reflow commentary
use quiet 8pt type. Medical text, table row/column labels, and vector equations are
retained. No medical content, source date, license, review status, or catalog pin
is changed by this typography work.

## Authenticated inputs available

The existing generated pack is
`.worktrees/49-reference-fonts/build/pdf-math/medical-a`. Its canonical generation
hash is `cdff7b842c7580f45454fc19752d7117f1b52b17813938b0911cd2055bb5a375`,
matching the existing `medical_phone_pdfs` catalog pin. The raw receipt hashes to
`3b5eb04f714dc4d50d5837a0701c6d7931797ed7d9bca28760529dc830dab902`;
its historical recipe is
`medpdf-v1-1ce9b2273f78a1ccfde201172e9159e86bfdae1af4943dbbc182a469c31181a4`.

A read-only admission pass verified every generated payload and both indexed
intermediates. All 158 cached HTML files match the ASCII SHA-256 stored in their
original PDF first identifiers. Each has one exact clinical `<main>` wrapper.
The HTML totals 40,597,470 bytes; the original payloads total 70,054,021 bytes.
All nine pinned fonts are available and rehashed, totaling 45,242,328 bytes.
No archived source or MathJax runtime was opened. This admission took 6.96 seconds
at one CPU and a 1 GiB cap, peaking at 178,364,416 bytes without OOM events.

The original pack records 15,786 phone pages across 158 articles, ranging from
11 to 421 pages. A bulk rerender's cost is not inferred from byte size. The first
bounded trial is the existing 11-page `crush_injury` article, followed by the
253-page `cardiopulmonary_resuscitation` article if the first passes. Freeze the
producer, then use separate fresh outputs, the pinned existing build image,
networking disabled, one CPU, and a 2 GiB cap. Measure actual exit, elapsed time,
peak memory, output size, body identity, and first-page readability before a
158-document batch. These trials are not a clean repeat pair or phone acceptance.

## Cache-only producer

`tools/recompose_medical_references.py` takes `--root`, `--prepared`, `--cache`,
`--output`, and explicit repeated `--topic` values, or the deliberate `--all` mode.
`--jobs 1|2` controls only rendering. Two workers use separate spawned processes,
one document per worker lifetime; admission happens once, and the parent writes
results in original topic order. Focused fixtures compare actual PDF bytes from
both worker counts. Timing telemetry is not a clean-pack reproducibility claim.
It verifies the existing generated catalog receipt, original PDF/HTML association,
intermediates, and font pins. It reuses exact clinical main-body bytes, cached
vector equations, original body styles, metadata, source links, and epoch.
It does not call archive admission, article extraction, MathJax, or a download.
The original pack and its pins remain untouched.

A new recipe binds the changed framing producer/templates, authenticated original
pack, selected topics, font inputs, shared PDF policy, and pinned environment.
The new receipt preserves original source and review holds, old/new clinical-body
hashes, updated page counts, license notices, and resource measurements. Selecting
fewer than all original articles produces `complete: false`. No catalog adoption,
review approval, raw-archive reproducibility claim, or normal assembly-gate change
is made. The new PDF IDs bind the exact newly generated HTML.

## How-to reference limitation

The selected six-article how-to pack at
`.worktrees/49-reference-fonts/build/reference-complete/reference_howto_1-a`
has PDFs, license files, article metadata, and an archive audit, but no cached HTML
or article body. Its article metadata explicitly excludes HTML. That pack cannot
use this authenticated cache-only reflow. It remains unchanged; quarantined
Wikibooks is neither read nor restored. The shared collection template change
applies to future eligible generation, without relabeling the historical pack.
