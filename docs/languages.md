# Language editions

`ck core` builds all fifteen editions by default. `--languages en es` is useful
for editing. Full images require all editions. English is a draft; Spanish and
the thirteen quick starts are unreviewed machine translations. No human review
has been recorded. The Census ranking remains an explicit release blocker.

Each edition has labels, a README line and rally-rule translations in
`content/<code>/edition.yaml`. Non-English prose defaults in `defaults.yaml`
are bound to the SHA-256 of their original config value. Times, channel numbers,
frequencies and mesh-channel names come directly from the shared config. RTL
editions isolate these left-to-right settings to preserve their order.

Spanish document front matter records hashes of the English source bodies.
Changing a protocol forces retranslation before rendering. Changing only its
review metadata does not. Hashes establish freshness, not translation quality.

Fonts are fetched from immutable publisher URLs in `catalog/fonts.yaml` and
verified before embedding. The PDFs use Noto Latin, Arabic, Devanagari, simplified
Chinese, traditional Chinese and Korean fonts. No font binaries belong in git.
The publisher does not supply SHA-256 files for these font sources, so human
review of the downloaded pins remains recorded as unresolved in the catalog.

Official translated preparedness guides and phrasebooks are separate catalog
items; the quick starts do not substitute for those imports.
