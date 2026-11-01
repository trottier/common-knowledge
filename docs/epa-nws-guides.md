# EPA and NWS guide intake

The 2026-11-01 intake measured four individual publisher PDFs, totaling
4,121,258 bytes and 10 pages. Source bytes live in the SHA-256 cache, not Git.
The catalog is `catalog/epa_nws_guides.yaml`; exact HTTPS responses, metadata,
PDF checks, and remaining holds are in
[the intake evidence](evidence/epa-nws-guide-intake.json).

| File | Printed edition or publisher file date | Bytes | Intake placement |
| --- | --- | ---: | --- |
| EPA emergency drinking-water disinfection, English | September 2017 | 754,723 | Held in `hub_only` |
| EPA emergency drinking-water disinfection, Spanish | June 2015 | 250,968 | Held in `hub_only` |
| NWS thunderstorm safety, English | November 29, 2018 file | 441,317 | Universal supplementary guide |
| NWS Weather Radio quadfold, English | January 2025 | 2,674,250 | Universal supplementary guide |

The [EPA English item page](https://www.epa.gov/ground-water-and-drinking-water/emergency-disinfection-drinking-water-0)
and [Spanish item page](https://espanol.epa.gov/espanol/desinfeccion-de-agua-potable-en-situaciones-de-emergencia-junio-de-2015)
still link different editions. Their page-update and PDF-creation dates do not
replace the printed edition dates. The Spanish bleach table covers one
concentration, whereas the English table covers two; other text also differs.
These files are not verified parallel translations. Intake preserves both
unchanged and does not transcribe doses, reconcile guidance, or approve the
existing START water-safety draft.

EPA author metadata and publication imprints identify its Office of Water, but
the instructional illustrations lack individual rights statements. The
[EPA disclaimer templates](https://www.epa.gov/web-policies-and-procedures/epa-disclaimers)
expressly require incorporation by reference; they supply no automatic grant for
these files. EPA's [copyright policy](https://www.epa.gov/irmpoli8/policy-and-procedure-posting-copyrighted-works-epas-website-and-intranet)
also recognizes rights in contractor and grantee works. Both candidates retain
unresolved license/proof markers, `hub_only` placement, and named legal review.
They cannot ship on that evidence alone.

The [NWS collection](https://www.weather.gov/owlie/publication_brochures) links
both weather PDFs and supplies its public-domain/reprint terms. Their mastheads,
credits, and rendered pages contain no identified excluded partner or separate
copyright restriction. The thunderstorm guide credits NOAA photographs and an
SPC chart. NWS attribution remains with each unchanged file; distribution must
not imply agency endorsement. Independent authorship and image-credit review
remains open. The [NWR All Hazards page](https://www.weather.gov/nwr/allhazards)
also links the same January 2025 quadfold. Its nationwide station list is dated
reference information, not a claim that any station currently operates or can
be received. It does not customize the kit by household or locality.

All four PDFs parsed and rendered; no encryption, attachments, root open action,
or scanned JavaScript/launch/additional-action keys were found. The thunderstorm
PDF has five URI link actions and a nonzero-indexed cross-reference warning;
the original bytes remain intact. These bounded checks do not establish complete
malware analysis, accessibility, clinical accuracy, or physical phone readability.
Independent computed-pin, currency, water-safety/medical, and safety/radio holds
remain in the catalog. No human review status was changed.
