# Wikivoyage phrasebooks

`ck phrasebooks --cache cache --output build/phrasebooks/all --epoch EPOCH` reads
`selection.yaml`, validates both source archives and builds one attributed phone
PDF for every edition. Run in the pinned build container without networking.
The output directory must be new; a failed edition prevents a partial set from
being presented as complete.

Fourteen editions use English Wikivoyage phrasebooks. The English phrasebook uses
Spanish Wikivoyage's **Guía de inglés**. The Chinese script editions share the
publisher's Mandarin phrasebook. Publisher explanations remain in English or
Spanish; these are imported reference works, not translations of START. The PDF
states its source language. It does not claim a reviewed translation.

The actual September 2026 ZIMs match Kiwix's metalink SHA-256 values. Every selected
article resolves in those snapshots. Revision links, localized edit dates and
CC BY-SA 4.0 notices are checked in the publisher footers. Shared reference code
removes active resources and unavailable figures, retains source text and table
cells, checks glyph coverage and page bounds and writes fixed-date tagged PDFs.
Attribution and the exact source revision travel in each PDF; audit HTML and
archive checks remain outside the placed payload.

All fifteen built successfully: 1,802 phone pages, 5,194,279 payload bytes. The
Hindi article also uses Gurmukhi and Tamil; its required fonts are pinned alongside
the other scripts in `settings.yaml`. No font file is committed. Conversion-pin,
language and physical phone reviews remain open. Two independent complete builds
matched every PDF, provenance audit and generation manifest.

The English source archive has three malformed internal links. It is a regeneration
input, not a placeable archive. Phrasebook PDFs sanitize their own navigation and
record that audit. The whole travel archive must pass strict validation after
regeneration before it can populate the in-depth collection. The measured rebuilt
archive passed strict checks and the complete entry comparison (205,100,476 payload
bytes). Its pin and physical reader reviews remain open.
