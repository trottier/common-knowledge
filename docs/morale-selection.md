# Initial morale books

The morale collection starts with seven individually checked Project Gutenberg
ebooks: *Alice's Adventures in Wonderland*, Townsend's *Aesop's Fables*,
*A Christmas Carol*, *Tom Sawyer*, *Pride and Prejudice*, *The Adventures of
Sherlock Holmes*, and the Spanish *Don Quijote*. Each entry in
`catalog/books.yaml` links to its own publisher page, which identifies the work
as public domain in the USA. The catalog records the downloaded UTF-8 text's
actual size and SHA-256, the publisher's update date, author and production
credits.

The embedded notices in all seven downloaded texts also state that their print
sources are not protected by U.S. copyright law. The complete original text is
shipped byte for byte, including every Project Gutenberg license and trademark
notice. No ebook text is stored in git. Human review of the pins and
redistribution terms remains explicit in the catalog.

These are optional plain-text books in the variant 8 collection. This initial
selection does not claim to supply a ZIM, a phone PDF edition, music, games, a
reviewed children's reading list, or literature in every edition's language.
The core continues to open as PDFs without an additional reader. The books
contain historical language and views; selection is not an endorsement.

The collection-wide Gutenberg placeholder has been replaced by these specific
items. Large subject archives are not selected on an assumption that every
included work has the same rights. Project Gutenberg distinguishes public-domain
works from copyrighted works distributed under individual permissions in its
[license explanation](https://www.gutenberg.org/policy/license.html).

To fetch the originals, run `ck fetch` with the seven `gutenberg_<number>`
identifiers in `catalog/books.yaml`. The ordinary fetcher checks each size and
SHA-256 before caching the file. Assembly uses the numbered `.txt` destination
from the catalog and copies the verified original bytes.
