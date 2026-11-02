# Local quick guides and copy-index attachment

`build_quick_guides.py` renders six unchanged original English and Spanish START
sections through the frozen project's renderer. It produces twelve unique PDFs,
with byte-identical destination copies for START and PHONE_PACK, plus an external
receipt. It preserves source status, body hashes, translation bindings, citations,
fonts, epoch, and a pagination snapshot. It does not edit the source content or
claim human approval. Run in the pinned build container with source/cache mounted
read-only and `CK_FONT_CACHE` pointing at the explicit cache.

`attach_copy_index.py` accepts an authenticated index/receipt and a manifest-verified
base tree, then creates a fresh clone with index copies in PHONE_PACK and BACKUP.
The receipt must identify the exact base manifest and every eligible original file.
No existing index or output is overwritten. A new self-excluding manifest and
external provenance retain the old manifest and index receipt. Supply optional
pinned base provenance to preserve the complete earlier component history.
The original tree, ordinary assembly gates, and human review status stay unchanged.

The attachment helper also accepts exactly `3_MAPS_AND_PLACES/0_FIND_A_MAP.pdf`
with an `indexed_maps` inventory matching the actual primary county PDFs. This
map finder gets no BACKUP copy and must precede the final copy index. These two
exact index paths do not grant permission for arbitrary overlays.
