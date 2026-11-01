# Selected Kiwix reader source inspection

Observed November 1, 2026, against catalog baseline `fc6c9f7`. This packet pins a
useful Android native-source subset and one exact Mac package source. It does
not establish complete corresponding source, redistribution approval, or
offline behavior for any reader. No installed application was launched, no
source was compiled, and no human review status changed.

[The original proposed records and additive graph](proposals/kiwix-source-graph.yaml)
are preserved as historical research. The four source records are now in
[the active catalog](../catalog/kiwix_sources.yaml), with additive Android and
Mac source edges in [the APK catalog](../catalog/apk.yaml). All four records
remain hub-only and review-blocked. [The static evidence](evidence/kiwix-source-audit-2026-11-01.json)
records original-byte hashes, archive members, and comparisons. All downloaded
payloads remain in the ignored, SHA-256-keyed cache. Computed SHA-256 pins still
need human review; matching a publisher MD5 is an additional consistency check.

The publisher's [Android release assets](https://github.com/kiwix/kiwix-android/releases/tag/v3.14.1),
[desktop directory](https://mirror.download.kiwix.org/release/kiwix-desktop/),
and [Mac directory](https://mirror.download.kiwix.org/release/kiwix-macos/)
did not identify a complete corresponding-source bundle for these selected
distributions. The evidence preserves the observed listings; this is a bounded
search, not a claim that no such bundle exists elsewhere.

## Android 3.14.1: a verified native subset

The selected APK's embedded `META-INF/version-control-info.textproto` names
`ecd3ca40b53c1e2429f01474bb39e42e07d1ea21`, matching its existing source pin.
That source's [version declarations](https://github.com/kiwix/kiwix-android/blob/ecd3ca40b53c1e2429f01474bb39e42e07d1ea21/buildSrc/src/main/kotlin/Versions.kt)
select `org.kiwix:libkiwix:2.4.0`. This is the Java/JNI binding version, distinct
from the C++ library version.

The binding's publisher tag resolves to
`40967ea319fc31beec0fb5240fb488c68e94f6f9`. Its exact
[Gradle recipe](https://github.com/kiwix/java-libkiwix/blob/40967ea319fc31beec0fb5240fb488c68e94f6f9/lib/build.gradle)
selects C++ libkiwix **14.1.0**, libzim **9.4.0**, NDK **27.3.13750724**, and
CMake **3.22.1**. The recipe names separate SDK archives for four Android ABIs;
it does not select the separately published libzim `9.4.0-1` SDKs.

The [published Gradle module metadata](https://repo.maven.apache.org/maven2/org/kiwix/libkiwix/2.4.0/libkiwix-2.4.0.module)
provides the AAR's SHA-256 and size. Both match the downloaded original. All
**20 native `.so` files in that AAR match the selected APK byte for byte**:
`libc++_shared`, `libkiwix`, `libkiwix_wrapper`, `libzim`, and `libzim_wrapper`
for `arm64-v8a`, `armeabi-v7a`, `x86`, and `x86_64`. This identifies the packaged
native artifacts; it is not a source rebuild. The APK's four
`libobjectbox-jni.so` files also match the separately published ObjectBox
4.1.0 AAR byte for byte, but its source and license chain remain unresolved.
The eight libkiwix/libzim SDKs named by the binding recipe were also downloaded;
their native library files match the APK exactly across all four ABIs, and
their MD5 values match the publisher's companion files. These SDKs supply
binary libraries and headers rather than complete dependency sources.

The full binding repository archive includes JNI/C++ source and build scripts.
Its published `sources.jar` repeats 31 Java paths in its central directory;
both copies of each file match the pinned repository. It contains no C++
source and is insufficient alone.
The [binding license declaration](https://github.com/kiwix/java-libkiwix/blob/40967ea319fc31beec0fb5240fb488c68e94f6f9/README.md#license)
is GPLv3 or later. The corresponding publisher C++ source archives are pinned
in the proposal; their MD5 values match the publisher's companion files.
Their README, Meson recipe, and COPYING bytes also match the resolved Git tags.

The [libkiwix declaration](https://github.com/kiwix/libkiwix/blob/0a9ba9b678f2775191234dea5567c7559176d736/README.md#license)
is GPLv3 or later. The [libzim declaration](https://github.com/openzim/libzim/blob/8ef511ba0de6a8180d79fbc3c7edcfec4202ae5e/README.md#license)
is GPLv2 or later; individual files include GPLv3-or-later headers, so the
top-level label does not replace per-file review. Libkiwix also contains
third-party skin assets, including an Apache-licensed autocomplete component.

Remaining Android work includes the complete resolved Maven graph, ObjectBox,
NDK/C++ runtime sources and notices, exact native build recipes and static
dependency sources, bundled assets, and binary/source correspondence. In
particular, the [C++ Meson recipe](https://github.com/kiwix/libkiwix/blob/0a9ba9b678f2775191234dea5567c7559176d736/meson.build)
declares dependencies such as ICU, curl, microhttpd, pugixml, zlib, and Xapian;
their source versions cannot be inferred from the top-level archive.

ObjectBox needs a specific license hold. Its exact
[4.1.0 POM](https://repo.maven.apache.org/maven2/io/objectbox/objectbox-android/4.1.0/objectbox-android-4.1.0.pom)
declares an **ObjectBox Binary Licence** for the native runtime, Apache 2.0 for
Flatbuffers, and OpenLDAP 2.8 for LMDB. The publisher's
[license FAQ](https://objectbox.io/faq/#license-pricing) distinguishes Apache
language bindings from the native runtime. Its linked
[binary terms](https://objectbox.io/0209-ob-binary-license/) contain restrictions
on modification and use, with a revocable, non-sublicensable grant. Confirm the
release-specific terms, complete native sources, and GPL compatibility with a
human reviewer; the Java repository's Apache license does not clear this
packaged runtime. The selected APK's former GPL-only catalog label was an
incomplete component inventory. Its active composite declaration now records
the known POM component licenses and an unresolved ObjectBox term marker, with
named legal review required. This does not infer that the current website
terms were the exact terms delivered with the older artifact.

## Windows and Linux 2.5.1: app source is not a distribution manifest

Both selected desktop binaries currently point to the same 685,967-byte app
source archive. Its [qmake project](https://github.com/kiwix/kiwix-desktop/blob/690251263462cebd8c4c7d65f8d26cd9e787cc83/kiwix-desktop.pro)
requires Qt WebEngine and other Qt components. The source's
[CI recipe](https://github.com/kiwix/kiwix-desktop/blob/690251263462cebd8c4c7d65f8d26cd9e787cc83/.github/workflows/ci.yml)
uses moving `kiwix-build` dependency actions and names Windows Qt 5.15.2.

Static inspection of the selected Windows ZIP instead finds Qt 6 DLLs whose
fixed version resources report **6.4.3.0**. It also includes OpenSSL, ICU,
aria2, QtWebEngineProcess, Chromium resource files, and
`vc_redist.x64.exe`. These observations identify additional source, license,
and notice work. They do not identify every dependency's exact source or
authorize redistribution of the Microsoft runtime. In particular, the CI
recipe above is insufficient as the selected Windows package's manifest.

The Linux AppImage's original hash was reverified without executing or
extracting it. Its complete embedded dependency and notice inventory remains
open. Do not assign the Android native versions to either desktop reader.
Obtain the actual packaging revision, dependency manifest, compiler/SDK pins,
Qt/Chromium source and notices, and all other bundled component obligations.

## Mac 3.17.1: one exact package, with native and resolution gaps

The selected source's [Brewfile](https://github.com/kiwix/kiwix-apple/blob/1dc9c867236f0b915e9e42b46df9fe36e1b35e78/Brewfile)
downloads `libkiwix_xcframework-14.2.1-2.tar.gz`. Thus the native framework has a
versioned input; it is not covered by the app archive itself. This packet does
not claim to have closed that framework's source graph.

The [project declaration](https://github.com/kiwix/kiwix-apple/blob/1dc9c867236f0b915e9e42b46df9fe36e1b35e78/project.yml)
pins Swift System to `b083113aef646d9d35403ca17e9789b750e42d1d`, which is fetched
and proposed as an additional source input. Its
[license text](https://github.com/apple/swift-system/blob/b083113aef646d9d35403ca17e9789b750e42d1d/LICENSE.txt)
contains Apache 2.0 and the Runtime Library Exception. The proposal preserves
the exception; it remains policy-blocked pending explicit human review.

Defaults and StripeApplePay are specified by version ranges. No
`Package.resolved` is present in the selected app source archive. The build
action requests resolved versions, but that does not supply the missing
release resolution record. Obtain the actual package lock, exact CoreKiwix
framework/source correspondence, native dependencies and notices, and selected
DMG provenance. The DMG hash was reverified, but it was not mounted or launched.

## Integration and review

The active graph retains each app's existing `source_id`, `source_url`, and
human review holds. The binding's native dependencies sit under its source
node; Swift System sits under the Mac source node. Adding these exact pins
does not clear per-file obligations, unfamiliar license expressions, source
closure, or human approval. ObjectBox native sources and terms, the full
Android dependency graph, desktop packaging manifests, and Mac's remaining
package/framework sources are still open. No claim of a complete publisher
source bundle is made.
