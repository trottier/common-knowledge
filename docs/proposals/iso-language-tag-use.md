# ISO language identifiers in video tracks

The [ISO 639 primary page](https://www.iso.org/iso-639-language-code), checked
November 1, 2026, explicitly permits free use of language identifiers. It also
identifies the Library of Congress as the agency publishing Set 2. This supports
using the identifiers as MP4 language tags; it does not establish a license to
redistribute the downloaded table, language-name lists, or standard text.

`LicenseRef-ISO639-Code-Use` records that narrow build use. Catalog checks restrict
it to the existing, unshipped Library of Congress input under `build/video/` with
`hub_only` placement. The video pipeline uses its identifiers and excludes the
table from output files and source notices. This is not a public-domain,
Creative Commons, or general redistribution claim.

The input URL, version, size, and SHA-256 are unchanged. Previously generated
videos retain their actual recipes and input hashes. Independent pin review,
video-specific rights and safety review, and device playback checks remain open.
The upstream waiting period remains TBD; no new upstream release is selected.
