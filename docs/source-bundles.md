# Exact source preservation

A publisher URL and revision number do not guarantee that a future request will
return the same bytes. WikEM parser output can change even for an old revision.
The source bundle commands preserve already verified raw downloads, including
all recursively declared inputs of a generated catalog item. They never fetch
new content, modify publisher bytes, approve rights, or mark a source reviewed.

Run in the pinned build container, with the catalog and source cache mounted:

```sh
ck source-pack wikem_en_nopic --cache cache \
  --output build/sources/wikem.tar.gz --epoch "$SOURCE_DATE_EPOCH"
ck source-restore wikem_en_nopic --cache restored-cache \
  --bundle build/sources/wikem.tar.gz --sha256 <published-bundle-SHA-256>
```

The gzip header has no filename or current timestamp. Tar members are sorted,
regular files with fixed ownership, modes and epoch. `sources.json` records each
raw input's full catalog entry, including its individual publisher URL, version,
license, attribution and proof URL. Payload names are their SHA-256 values;
identical downloaded bytes are stored once. The tool reports the finished
bundle's actual size and SHA-256 for external publication.

Restoration first verifies that external bundle hash, then exact catalog records,
member names, types, completeness, sizes and every payload hash. No archive path
is extracted directly. Files are published to the cache only after the entire
archive passes; corrupt existing cache entries are not replaced. The normal
builder still performs its own input validation and archive checks afterwards.
Use a new bundle when the source catalog changes, including attribution or
review fields. Keep the matching tagged catalog with every published bundle.

This is source preservation tooling, not a GPL corresponding-source closure or
release publication. Human review, stable hosting and release attachment policy
remain open. Check the actual bundle against the GitHub release size limit
before publishing. Cargo and source bundles stay outside git.


At development epoch 1793404800, two independently packed WikEM bundles match, and a third pack in the pinned
Linux amd64 container produces the same bytes:
20,331,490 bytes, SHA-256
`35bc225dbfba105939d60b709740d2a8ba2277252ba9b6c8257811a3d0ecac36`.
A separate empty cache restored all 4,655 raw source items successfully. This is
measured local packaging evidence, not a stable-hosting or release claim. The
payload, matching catalog snapshot and source-selection exclusions still need
human review before distribution.


A subsequent full WikEM build used only the restored cache in a network-disabled
Linux amd64 container. Its 4,278 articles, 6,641 redirects, 8,601,054-byte payload
and generation manifest matched the earlier independently built archive exactly.
Strict `zimcheck` passed. This confirms actual offline restoration for that
snapshot, while clinical review and physical reader testing remain outstanding.
