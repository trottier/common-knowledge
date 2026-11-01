# Language edition selection

On 2026-10-31, the publisher confirmed: keep the specified fifteen editions,
order them by Census limited-English-proficiency counts, and document the
selection exception. This preserves English, Spanish, Simplified and Traditional
Chinese, Vietnamese, Korean, Tagalog, Arabic, Haitian Creole, Russian,
Portuguese, French, Persian, Polish and Hindi.

The order uses the United States row (`0100000US`) in
[2025 ACS one-year table B16001](https://www2.census.gov/programs-surveys/acs/summary_file/2025/table-based-SF/data/1YRData/acsdt1y2025-b16001.dat).
It counts people aged five and over who speak a language at home and report
speaking English less than “very well.” It does not rank all speakers of each
language. English stays first as the full default edition. The remaining
selected editions follow their LEP point estimates, retaining Simplified then
Traditional Chinese as adjacent editions of the same Census group.

This is a publisher-selected set, not a claim to cover the thirteen largest
individual non-English languages. The table puts Bengali (197,440) and Japanese
(184,363) above Polish (164,694) and Hindi (151,334). It also combines some other
languages into broader categories, including Afro-Asiatic, Slavic and Indic
groups. Those categories cannot be assigned to one translated edition without
additional evidence. Chinese writing systems do not have separate estimates.
Estimates also have sampling margins of error; the audit retains them.

`config/languages.yaml` is the edition-order source of truth. The mapping in
`pipelines/languages/settings.yaml` identifies the Census variables. The input
table and publisher table-shell dictionary are pinned in `catalog/geodata.yaml`.
The publisher's [2025 dataset metadata](https://api.census.gov/data/2025/acs/acs1.json)
identifies `ACSDT1Y2025` and its CC0 license. A metadata record for an older ACS
year is not used as proof for this release.

Run the audit inside the build container after fetching its two catalog inputs:

```sh
rtk proxy docker run --rm --network=none --platform linux/amd64 \
  --volume "$PWD/cache:/cache:ro" --volume "$PWD/build:/artifacts" \
  common-knowledge-build:dev ck languages-audit \
  --cache /cache --output /artifacts/languages-audit.json
```

The command reads the public table-based files, so it needs no Census API key.
It derives the LEP variables from the publisher's hierarchy, rejects missing or
suppressed estimates, and reports whether the current selection is in estimate
order. It does not silently add, remove or approve editions. Source-pin review
and translation/device review remain separate release gates.
