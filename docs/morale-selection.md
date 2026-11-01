# Initial morale collection

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
selection does not claim to supply a ZIM, phone PDF editions of the text books, a
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


The games section adds Clarence Squareman's *My Book of Indoor Games*,
[Project Gutenberg #13022](https://www.gutenberg.org/ebooks/13022), updated
2024-10-28. Its publisher page and complete embedded license identify the text
as public domain in the USA. The original UTF-8 text, production credits and
license are retained. Historical game instructions still need suitability
review; they are not emergency or child-safety protocols.

The music section adds D. A. French's 1875 piano variations *Home sweet home*,
[Library of Congress item 2023822433](https://www.loc.gov/item/2023822433/).
The item's rights statement identifies the Music for the Nation collection as
public domain and free to use and reuse, and gives the Music Division credit
line. Its eleven-page publisher PDF is copied without changes. This supplies
notated music; no recording or performance rights are inferred from the score.
Neither optional item requires an app installation. Physical readability and
human review of both download pins remain open.

The actual downloaded games text measures 216,142 bytes; the music PDF measures
2,923,777 bytes. Their SHA-256 values and individual proof pages are recorded in
`catalog/books.yaml`. Downloaded files and captured source metadata stay in the
ignored cache and research folders, outside git.
