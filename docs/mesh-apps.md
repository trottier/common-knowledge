# Mesh app provenance

The catalog pins the publisher's original APKs. Neither APK is modified.
Physical installation, offline peer communication and sharing remain unchecked.

## bitchat Android

The official [bitchat website](https://bitchat.free/) links to
`permissionlesstech/bitchat-android`. The selected
[v2.2.0 release](https://github.com/permissionlesstech/bitchat-android/releases/tag/v2.2.0)
publishes a universal phone APK, checksums and `BITCHAT_BUILDINFO.json`.
The downloaded universal APK matches the release SHA-256 and size. `apksigner`
verifies it with certificate SHA-256
`3b03fa66a5451321100792f5b55a7b4966d5c8dc10c6daa40aa95ea489531bca`,
matching the publisher's release documentation.

Build information identifies commit
`20501fdfe0d56c7705c377d4a263b01d8f38eeeb`. The source archive uses that
commit; its LICENSE.md is GPLv3. The website's older public-domain sentence is
not used as license evidence for the Android release. Its native Arti build,
Cargo dependencies and Gradle dependencies still need complete corresponding
source and notice review. The archive alone does not close that review.

## Briar

The [official download instructions](https://briarproject.org/installing-apps-via-direct-download/)
link to the publisher APK. Its bytes match the versioned `briar-1.5.24.apk` in
the publisher's [F-Droid repository index](https://briarproject.org/fdroid/repo/index-v1.jar):
version, size and SHA-256 all agree. `apksigner` verifies certificate SHA-256
`501ddf14a6ecf904fb20285c56a565cb987a867f91572ee33c2d43771cca4e37`,
also matching the index's signer field.

The APK's version-control metadata identifies
`fbfebc4242f09e996a867de7988683628d426534`, which agrees with the publisher's
`release-1.5.24` tag. The source archive is pinned to that commit. Its
`.gitmodules` and Git tree identify the mailbox submodule at
`64147fd1d09764500c77948204c998aa6cfec347`; that archive is pinned separately
and included as a corresponding-source dependency. Remaining libraries,
native components and build dependencies still require source-closure review.

The publisher APK includes unsigned metadata entries reported by `apksigner`.
Those bytes are retained unchanged; the pinned whole-file SHA-256 covers them.
The source copyright license is GPLv3; no trademark endorsement is claimed.

## Drive and release output

The apps land at `8_MESH_CHAT/bitchat.apk` and `8_MESH_CHAT/Briar.apk`.
Original publisher license files land under `8_MESH_CHAT/LICENSES/`.
`SOURCE.TXT` is generated from the placed app catalog entries, including their
versions, APK checksums, signer fingerprints and exact source URLs.

Release packaging follows declared source dependencies and preserves every
archive byte. It recognizes the archive's actual format, because publisher API
URLs do not always end with a filename extension. Cycles are rejected. No source
pin, legal review or physical test is marked reviewed by this implementation.

PocketPal already fills the Android GGUF-reader role. Its obsolete unselected
`android_gguf` catalog placeholder has been removed; a second unknown reader is
not an additional drive requirement.
