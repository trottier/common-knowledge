# Geographic source-name fonts

The national point snapshot includes Cherokee, Arabic and Chinese names that
the Latin/Greek/Cyrillic Noto Sans font cannot render. Do not translate, replace
or omit those source names to make a PDF build pass.

`pipelines/geodata-fonts.yaml` selects the ordered, catalog-pinned font set for
atlas legends and directories. Noto Sans remains first, followed by Arabic,
Simplified Chinese and Cherokee fonts. These are build inputs; PDFs embed
subsets. No font binaries are committed.

The Cherokee file is the publisher's Noto Sans Cherokee version 2.001 at commit
`57b4ebace8a7b5b3cb05bf92d84bb5de27894698`. The complete HTTPS download matches
the catalog's measured 224,360-byte size and computed SHA-256. Its exact-commit
[OFL license](https://github.com/google/fonts/blob/57b4ebace8a7b5b3cb05bf92d84bb5de27894698/ofl/notosanscherokee/OFL.txt)
permits embedding and redistribution under its terms. Human font-pin review
remains open.

Before preparing atlas jobs, the build checks source names against the fonts'
Unicode character maps. Directory builds check their complete draft text.
Missing characters fail with code points and Unicode names; a missing-glyph
box is not accepted as output. Whitespace and formatting controls do not need
visible glyphs. Glyph coverage alone does not establish correct shaping or
physical readability.

Every selected font's exact hash appears in the generated PDF inputs. Atlas
composition rechecks the ordered set against the jobs. PDF identity uses font
IDs and hashes rather than cache paths, so moving an identical cache does not
change the output.

The earlier 254,062-place snapshot passes coverage checks for names, addresses,
county names, and detail values. Tests also render Cherokee, Chinese, and Arabic
text into a phone PDF, check embedded fonts and extractable source characters,
and confirm identical atlas PDFs after relocating the font cache. Device tests
and human source-pin reviews remain separate release requirements.

The November 1, 2026, [corrected-corpus audit](evidence/geographic-font-corrected-corpus.json)
checks all 254,873 places, all 3,235 county labels, and all 56 current atlas job
files covering 4,115 map pages. Every observed visible character maps to the
existing four pinned fonts: 188 distinct code points in the directory fields
and 181 in the atlas titles, coordinate labels, and legend fields. The audit
independently rehashes both point-source files and all four cached fonts. This
corpus needs no additional font or pipeline change.

Six source places use 36 characters beyond the primary Noto Sans cmap. Four
places need Cherokee, one needs Chinese, and one needs Arabic. Two of these
cases occur in addresses rather than names. All six come from `geofabrik_us`.

| Source place ID | Field | Existing fallback |
| --- | --- | --- |
| `osm-w1424247992` | Tahlequah Fire Station address: `ᏓᎵᏆ` | Cherokee |
| `osm-w1209629398` | Tahlequah Post Office name | Cherokee |
| `osm-n8813107045` | `利达快递` name | Simplified Chinese |
| `osm-w591942914` | Cherokee Indian Hospital name | Cherokee |
| `osm-n13207413826` | CHEROKEE address | Cherokee |
| `osm-n14133849281` | Saad's Pharmacy Arabic name | Arabic |

Inspection of six completed phone/print county-part PDFs confirms source
fallback characters in extracted text and embedded font programs on the
matching pages. These cover the Chinese, Arabic, and North Carolina Cherokee
cases. The two Oklahoma directory cases were still being built; their source
characters pass the same cmap check. A scan of 227 observed renderer and final
run logs finds no matching font/glyph failure messages. The active directory
log is recorded as a byte-prefix snapshot.

The native basemap renderer uses the first pinned Noto Sans font for vector-tile
labels. This audit enumerates directory and atlas job text; its receipt records
that native tile feature text was not independently enumerated. Glyph mapping,
PDF text extraction, and embedded fonts remain separate from shaping and phone
readability checks.

Existing tests separately check missing-character failures, the three geographic
scripts' PDF extraction, Arabic shaping through HarfBuzz, atlas raster presence,
and stable PDF identity after moving the font cache. Imported reference-article
PDF tests also check missing-symbol rejection and retained source numbers.
The unchanged Ready.gov imports have PDF parsing checks rather than a font
fallback or raster/readability assertion; see [official guides](official-guides.md).
Their font and image resources remain as published.
