# Drive trees and images

Run `make check dev` from a clean checkout to validate and produce a development
image for variant 1. `make clean` removes the ignored `build/` directory before
a clean rebuild. The Make target derives the development epoch from the actual
checked-out commit; release builds must use the confirmed configured epoch.

`ck core` produces a manifest of its PDF and HTML outputs and a fingerprint of
the source recipe, configuration, templates, catalog, code, lockfile and epoch.
Assembly rejects stale or changed core outputs. Do not mix profiles or epochs.

`ck plan --profile P --core PATH` reports each variant, known bytes, capacity,
largest items and every unresolved selected input. Unknown sizes do not become
zero, and overflows never cause automatic content removal. An explicit
`--capacity-bytes` argument is a planning assumption; images use configuration.
The publisher identified a nominal 32 GB part. Measured production usable bytes
remain unconfirmed in configuration.

`ck assemble --variant N --profile P --core PATH --output NEW_DIRECTORY` writes a
new tree atomically. Catalog files are copied unchanged after verification.
Generated items need a matching pipeline manifest and exact output hashes.
Full assembly requires the release gate and all fifteen rendered editions.

The tree contains primary documents, the phone pack and exact BACKUP copies.
Symlinks, reserved or colliding FAT names, oversized FAT files, autorun files and
executables outside allowed folders are rejected. Every file's mtime is fixed.
Final physical tree bytes are checked again against capacity, including metadata.

`ck image --variant N --profile P --core PATH --output NEW_DIRECTORY` creates
the FAT32 image with the configured label and serial, inserts directories and
files in sorted order, and hides BACKUP. `mkfs.fat --invariant` fixes filesystem
initialization. The pinned Python pipeline then normalizes FAT directory creation,
access and write timestamps, leaving long-name entries and file payloads intact.
FAT write times have the format's two-second precision.

The builder reads files back with mtools and verifies the complete manifest. It
publishes the image hash, a copy of its internal manifest, the manifest hash,
a recursive listing, and a deterministic single-threaded `zstd -19` compressed
image with its hash. No root mount or loop device is required.

The publisher approved one specification correction: MANIFEST.SHA256 covers
every other image file. Its own checksum is published outside the image to avoid
a circular dependency. AGENTS.md and CLAUDE.md record the same rule.

Tests use actual FAT images with Latin and Arabic long names, hidden BACKUP,
manifest readback and two builds with deliberately different source mtimes.
They compare both raw and compressed image hashes. Full sample-profile
reproducibility remains a separate requirement once its real inputs are pinned.
