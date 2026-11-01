# Reference collection sources

The catalog separates publisher inputs from the editions intended for a drive.
A confirmed download checksum establishes the input's bytes. It does not establish
that an archive is suitable for offline use, that every non-text asset has the
same license as its articles, or that the resulting drive fits its capacity.

## Simple English Wikipedia and Wikibooks

The selected publisher inputs are Kiwix's September 2026 Simple English Wikipedia
and October 2026 English Wikibooks editions, both without pictures. The catalog
records the exact sizes and SHA-256 values from their official `.meta4` files.
These raw inputs are `hub_only`; neither is copied into a drive's collection.

The corresponding generated entries target the `simplewiki` and `school`
collections. Their sizes, output checksums and recipe identifiers remain
unconfirmed until complete builds pass `zimcheck`. Use `ck offline-zim --item`
with the publisher input identifier. The regeneration pipeline retains articles,
tables, redirects, original attribution and revision notices. It repairs audited
broken links and external embeds with an adaptation notice; it preserves title
search and omits the publisher's full-text index. Two independent builds must
match before reproducibility is claimed.

[Simple English Wikipedia's copyright policy](https://simple.wikipedia.org/wiki/Wikipedia:Copyrights)
and [Wikibooks' copyright policy](https://en.wikibooks.org/wiki/Wikibooks:Copyrights)
describe the text licenses and attribution requirements. Non-text media require
their own license checks. The absence of photographs in a `nopic` archive does
not itself certify all retained resources. The catalog keeps that check explicit.

## Other candidate collections

Current PhET downloads are excluded under the publisher's current terms; see
[the permission record](permission-requests.md). Wikibooks is being built as an
alternative school reference. This selection does not claim that it replaces a
reviewed curriculum or that its contents have received educational review.

Appropedia's [intellectual property policy](https://www.appropedia.org/Appropedia:Intellectual_property)
allows exceptions to its default article license. Its embedded media may also
have different terms. The aggregate candidate remains unconfirmed; the default
license is not evidence for every file in that archive.

Project Gutenberg's [license](https://www.gutenberg.org/policy/license.html)
distinguishes unrestricted works from copyrighted works distributed with an
author's permission. A whole subject archive is therefore not accepted merely
because it comes from Project Gutenberg. Individual selections must have both
publisher metadata and the embedded ebook license checked. Complete original
texts and their license notices must remain available alongside any reformatted
edition. No selection is made from the large literature archives solely on the
basis of an approximate size or a collection-wide public-domain claim.
