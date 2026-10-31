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

The full 254,062-place snapshot passes coverage checks for names, addresses,
county names and detail values. Tests also render Cherokee, Chinese and Arabic
text into a phone PDF, check embedded fonts and extractable source characters,
and confirm identical atlas PDFs after relocating the font cache. Device tests
and human source-pin reviews remain separate release requirements.
