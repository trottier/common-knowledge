# bitchat build alternatives investigated on 2026-11-01

No current publisher-supported, Google-SDK-free APK was established in this
research. The selected 2.2.0 release remains unchanged. There is a concrete
historical MIT-licensed candidate, described below, whose present support,
compatibility, security, and device behavior have not been established.

## Current builds and F-Droid

The [official 2.2.0 release](https://github.com/permissionlesstech/bitchat-android/releases/tag/v2.2.0)
offers phone ABI/universal builds, Wear builds, and Play upload bundles. It does
not identify a FOSS or no-Google flavor. The pinned
[application build](https://github.com/permissionlesstech/bitchat-android/blob/20501fdfe0d56c7705c377d4a263b01d8f38eeeb/app/build.gradle.kts)
unconditionally declares the GMS location and ML Kit dependencies. Its build
file has no product-flavor selection that removes them. Running on a device
without Google Play services would not, by itself, establish absence of the
SDKs or their metrics behavior.

[Upstream PR #633](https://github.com/permissionlesstech/bitchat-android/pull/633)
proposed replacing Google location with the Android API and ML Kit scanning
with ZXing. It is closed and unmerged; its head is
`180d0b595ac973df103fe278a0c7327c64f53d72`. It is evidence of an attempted
alternative, not a selected or publisher-maintained release.

[F-Droid inclusion MR !24907](https://gitlab.com/fdroid/fdroiddata/-/merge_requests/24907)
is also closed and unmerged. On the research date, the official F-Droid package
page for `com.bitchat.droid` and its `fdroiddata` metadata-file endpoint returned
HTTP 404. Those checks do not prove that no third-party fork or repository
exists; no qualifying official F-Droid build was found.

## Historical candidate: 0.9.0

The [official 0.9.0 release](https://github.com/permissionlesstech/bitchat-android/releases/tag/0.9.0)
was published on 2025-08-22. Its source commit is
`848cffee07ba233741bd8479cb0829d846a62a75`, and its original
[license](https://github.com/permissionlesstech/bitchat-android/blob/848cffee07ba233741bd8479cb0829d846a62a75/LICENSE.md)
is MIT. The inspected build and version-catalog files declare neither Google
Play Services nor ML Kit. Of the 39 published release tags inspected, this is
the newest whose two build files lack those dependency markers. That is a
source inspection result, not proof of runtime behavior or current maintenance.

The original publisher APK was downloaded without modification and checked:

| Field | Observed value |
| --- | --- |
| File | [bitchat-0.9.0.apk](https://github.com/permissionlesstech/bitchat-android/releases/download/0.9.0/bitchat-0.9.0.apk) |
| Size | 3,285,411 bytes |
| SHA-256 | `4df226523ddc1fddb6c6a8f4c07f72bd1c72ebe8d0c958587e8b34c55c636edb` |
| Publisher checksum | Matches the official GitHub release-asset digest |
| Signature | `apksigner` verifies APK Signature Scheme v2 |
| Signer certificate SHA-256 | `3b03fa66a5451321100792f5b55a7b4966d5c8dc10c6daa40aa95ea489531bca` |

The signer is the same publisher key recorded for the selected GitHub 2.2.0
APK. The 0.9.0 APK has four Graphics Path native libraries. A case-sensitive
static DEX search for `com/google/android/gms`, `com/google/mlkit`, `firebase`,
`crashlytics`, and `analytics` found no matches. Such a search cannot prove that
all network or telemetry behavior is absent. No APK was installed or run in
this research.

The unchanged source archive at the exact commit was also downloaded: 413,647
bytes, computed SHA-256
`9cb00580bcfe1dd19c78a953cdac15e296fc8f67ef8f4c48a7efb0ef82e4f30b`.
Its README and command processor implement `/join` channels. The release notes
identify compatibility with iOS 1.3.1; they do not establish compatibility with
current releases. A source-to-APK rebuild, full dependency/notices audit,
contemporary protocol and security review, and physical offline/no-telemetry
checks remain necessary before considering a selection change.

Rebuilding unmodified current 2.2.0 source preserves its declared Google SDK
dependencies. The inspected source exposes no supported build switch to remove
them. Applying the unmerged PR or editing dependencies would be a separate
third-party-source change, not reproduction of the existing publisher release.
No such change or permission request was made.

## Native release-source revision evidence

The publisher's release notes identify the following AndroidX source revisions:

| Artifact | Publisher release-linked revision | Source inspected |
| --- | --- | --- |
| [Camera Core 1.6.1](https://developer.android.com/jetpack/androidx/releases/camera#1.6.1) | `987b9ac8585b31424a397206c492196dd163997b` | [JNI source directory](https://android.googlesource.com/platform/frameworks/support/+/987b9ac8585b31424a397206c492196dd163997b/camera/camera-core/src/main/cpp/) |
| [Graphics Path 1.0.1](https://developer.android.com/jetpack/androidx/releases/graphics#graphics-path-1.0.1) | `8a05a22af450d589ef911d772a001a49dcb05b71` | [Native source directory](https://android.googlesource.com/platform/frameworks/support/+/8a05a22af450d589ef911d772a001a49dcb05b71/graphics/graphics-path/src/main/cpp/) |

The Camera Core CMake file defines the two JNI libraries already matched to the
APK and links image processing against libyuv. Its Gradle wrapper references
the separate AOSP `external/libyuv` checkout; that external revision still needs
an exact publisher build-manifest binding. The Graphics Path CMake file lists
`Conic.cpp`, `PathIterator.cpp`, and `pathway.cpp` for its matching native library.

These are release-linked source candidates, not a successful binary rebuild or
complete native corresponding-source set. No latest-main source was substituted,
and no native source pin or catalog selection was changed by this research.
