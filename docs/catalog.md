# Catalog and fetch verification

Every selected external file needs its own entry. Family-level candidates are
explicit unresolved entries until they are split into actual publisher files.
Unknown URLs, versions, sizes, hashes and licenses use VERIFY markers. They must
not be replaced with approximate values from the project brief.

`ck validate` validates configuration, catalog structure, placements, unique ids
and generated-input dependencies. `ck validate --release` also rejects unresolved
markers, absent legal sign-offs, missing GPL source references and English
content without named human reviews. A valid development catalog is not a release.

`ck catalog` regenerates `THIRD_PARTY.md`. `ck fetch ID...` downloads confirmed
publisher files to `cache/<sha256>`. It checks the exact size and SHA-256, rejects
HTTPS downgrades, checks ZIMs with `zimcheck --all`, and checks APK signatures
against their pinned certificate. In Debian the `zimcheck` binary comes from
`zim-tools`; Kiwix readers are separate catalog cargo.

Downloads are streamed with a size bound, verified before an atomic rename,
and removed after any verification failure. Existing cache files are checked
again before reuse. Publisher files are not modified.

A downloaded hash without a publisher checksum can be quarantined for review.
It cannot be placed or released while its review marker remains. Fonts are
build inputs with that same explicit human pin-review requirement; the bootstrap
permits development rendering while release validation rejects the open review.

Source references:

- [Kiwix publisher Metalink checksum format](https://github.com/kiwix/kiwix-android/wiki/Creating-a-local-kiwix-download-server)
- [openZIM tools](https://github.com/openzim/zim-tools)
- [Debian apksigner](https://packages.debian.org/en/bookworm/apksigner)

The font catalog is JSON-compatible YAML so its pre-environment bootstrap can
use only the standard library. Other catalog families use the same schema.
