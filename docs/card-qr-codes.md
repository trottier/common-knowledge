# Card QR codes

The card's three destinations derive from `config/build.yaml`'s single
`site_base_url`: the videos page, state-emergency-agencies page and verification
page. One shared route list controls the card URLs and generated site filenames.
The site URL must use HTTPS without credentials, query parameters or a fragment.

Segno generates vector QR images locally. The images include a four-module quiet
zone and render at 25 mm on the half-letter card. Each code and label also links
to its destination in the PDF. English and Spanish cards remain two pages; the
Spanish translation notice remains on both pages. No network request occurs
while rendering or opening the card.

An unset `[[VERIFY: ...]]` site URL remains a yellow, non-scannable placeholder.
The code does not turn a marker or an unannounced GitHub Pages address into a QR
code. The current publisher URL remains unconfirmed, and the site is not yet
published. Confirm the public URL and deploy all three pages before releasing
printed cards.

The generated videos page lists confirmed publisher source downloads and explains
where MP4 files sit on the drive. It does not imply that source downloads use the
drive's normalized format. The agency page links to the pinned catalog's federal
USAGov agency directory and points offline readers to the drive's directory.
These static pages have no scripts, analytics or automatic remote resources.

Validation uses the deliberately non-published fixture base
`https://example.invalid/common-knowledge/`. Container tests check both card
layouts, all PDF links, invalid configuration and generated-page navigation.
An independent Apple Vision barcode scan of 140 dpi rasterizations recovered
all three exact URLs from each English and Spanish card. This is a rendered-file
check; it does not replace scanning the printed card on the physical phone
checklist.

Two separate card renders also produced identical English and Spanish PDF
hashes for that fixed fixture URL and epoch. The full container suite passes
212 tests; the focused card, site, core and configuration checks pass 43 tests.
