# Catalog license expressions

Catalog declarations remain byte-for-byte publisher strings. The policy parser
interprets `AND`, `OR`, parentheses, and Cargo's deprecated `/` separator without
rewriting the catalog or weakening the exact source-manifest audit.
[Cargo's manifest reference](https://doc.rust-lang.org/cargo/reference/manifest.html#the-license-and-license-file-fields)
documents license choices and the historical slash separator.

The parser follows [SPDX expression precedence and case rules](https://spdx.github.io/spdx-spec/v2.3.1/SPDX-license-expressions/):
license IDs are case-insensitive, operators are case-sensitive, and `AND` binds
more tightly than `OR`. A slash is interpreted as `OR`. The entire declaration
must parse before a known alternative can satisfy the catalog policy.

An unknown license cannot satisfy an operand. An unknown operand in a valid
`OR` expression may be bypassed by a supported alternative; an unknown required
`AND` operand blocks the expression. The exact `Apache-2.0 WITH Swift-exception`
pair is recognized; other exception pairs remain unsupported, but a separate
supported `OR` alternative can apply. For example,
`Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT` is supported through its
unexcepted Apache or MIT alternative. The exception branch itself is unsupported.

Malformed expressions, unknown operators, unmatched parentheses, trailing text,
unsupported document references, and excessive size or nesting fail closed.
This is a small policy subset, not a complete SPDX implementation. The existing
`US-PD`, `Public-domain-US`, and scoped Ready.gov license aliases remain explicit
project policy entries. Unrecognized license IDs and exception branches are not
silently added to that policy.

## Additional source licenses

The pinned bitchat Rust source set uses the following licenses beyond the
previous catalog allowlist. Their primary texts permit redistribution subject
to their terms; recognizing those declarations is not a claim that an entire
application complies with all applicable terms.

| Catalog identifier | Primary text and obligations to review |
| --- | --- |
| `Unlicense` | [Unlicense text](https://unlicense.org/): permits source and compiled distribution for commercial or noncommercial purposes. Retain the publisher's original declaration. |
| `Zlib` | [zlib license](https://zlib.net/zlib_license.html): retain its notice, identify altered source versions, and do not misrepresent origin. |
| `Unicode-3.0` | [Unicode License V3](https://www.unicode.org/license.txt): retain copyright and permission notices in the copies or associated documentation; observe restrictions on promotional use of rights-holder names. |
| `MPL-2.0` | [Mozilla's license text](https://www.mozilla.org/en-US/MPL/2.0/), especially sections 2.1 and 3.1–3.4: preserve covered-source licensing and notices, and make covered source available when distributing executables. |
| `LGPL-3.0-only`, `LGPL-3.0-or-later` | [GNU LGPL version 3](https://www.gnu.org/licenses/lgpl-3.0.txt) incorporates GPLv3 with additional permissions. Review source, notices, relinking, and applicable installation-information requirements. The later-version option depends on the publisher's declaration. |
| `GPL-2.0-or-later` | [SPDX's GPLv2-or-later text and identifier](https://spdx.org/licenses/GPL-2.0-or-later.html), especially sections 1–3 and 9: retain notices and licensing, provide corresponding sources for executables, and preserve the publisher's later-version choice. Recognition does not decide which version governs a combined application. |
| `OLDAP-2.8` | [OpenLDAP's original 2.8 license](https://www.openldap.org/software/release/license.html): retain source notices, reproduce applicable notices and disclaimer with binaries, and include the complete license document. Observe its restriction on promotional use of rights-holder names. This recognizes LMDB's declaration, not ObjectBox's separate binary terms. |
| `Apache-2.0 WITH Swift-exception` | [Swift's original license and runtime exception](https://www.swift.org/LICENSE.txt), with the [SPDX exception identifier](https://spdx.org/licenses/Swift-exception.html): the exception adds a limited attribution permission for qualifying compiled products. The parser recognizes the exact pair without deciding whether a particular distribution qualifies. Original licenses and notice obligations remain subject to source and human review. |

The 466 current Rust source declarations parse as supported expressions. All
466 still retain their independent human review holds. Their source archives
remain linked to the parent GPL application's corresponding-source graph.
Per-file licenses, notices, exact source correspondence, binary compatibility,
and fulfillment of source or relinking obligations still require human review.
The parser grants no legal, pin, content, or device-test approval.

## Contextual gates

All mentioned license IDs remain available after parsing. A shipped application
mentioning GPL, LGPL, or MPL requires a corresponding-source catalog entry, even
when an `OR` alternative is permissive. The release source collector uses the
same rule and follows the existing dependency graph. This conservative packaging
policy does not decide which license governs a combined application.

Noncommercial declarations still require a written emergency-use grant and
named legal review. An `OR` alternative cannot bypass those existing holds.
Ready.gov's narrow unchanged-document grant remains restricted to its official
documents and proof URL, outside in-depth collections, including when grouped
inside an expression. VERIFY markers, excluded-material rules, required legal
sign-offs, and human content-review gates remain in place.
