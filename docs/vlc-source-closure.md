# VLC Android source checkpoint

All eight standard native libraries in the two pinned VLC Android 3.7.1 APKs
match exact publisher AAR members. The APKs use the LibVLC 3.7.0 and medialibrary
0.13.17 artifacts requested by the pinned application build file. Both
`libc++_shared.so` copies match the medialibrary AAR, rather than the different
copies in the LibVLC AAR. The complete hashes and archive bindings are recorded
in [the evidence](evidence/vlc-native-sources.json).

This checkpoint adds nine catalog entries: two compiled artifacts used only for
provenance checks, two published Java source JARs, four native project source
archives, and the recipe-selected SQLite source. Both application-source entries
retain their existing inputs and link the seven source archives transitively.
The compiled AARs are not corresponding-source inputs and are not placed on a
drive. No application, source-pin, license, or physical-device approval is granted.

## Publisher bindings

The selected [APK distribution directory](https://get.videolan.org/vlc-android/3.7.1/)
lists APKs and their checksums. The source subset below comes from the exact
application recipe and its upstream references, rather than a newer VLC checkout.

| Component | Pinned identity | Binding |
| --- | --- | --- |
| Android application | `baeb1edae0678927ebe16d482d979e9c7e75ead6` | Existing APK source pin and application build files |
| LibVLC publisher artifact | `org.videolan.android:libvlc-all:3.7.0` | APK `libvlc.so` and `libvlcjni.so` match for both selected ABIs |
| Medialibrary publisher artifact | `org.videolan.android:medialibrary-all:0.13.17` | APK `libmla.so` and `libc++_shared.so` match for both selected ABIs |
| LibVLCJNI source | `7cd0c151da4162aa3052fb6949ddab1436d8fafb` | Application `buildsystem/compile.sh` |
| VLC native source base | `3458be162f476ff64b639140b684efa1143ddeea` | LibVLCJNI `buildsystem/get-vlc.sh`, followed by its 20 retained patches |
| Medialibrary native source | `8c56e26c625d757994cffeea84d2a0a2e6033dee` | Application `buildsystem/compile-medialibrary.sh` |
| libvlcpp source | `44c1f48e56a66c3f418175af1e1ef3fd1ab1b118` | Exact medialibrary Git submodule entry, followed by the application recipe's one patch |
| SQLite source | `sqlite-autoconf-3460100.tar.gz` | Application compile script; downloaded bytes match its published SHA-512 |

The [LibVLC](https://repo.maven.apache.org/maven2/org/videolan/android/libvlc-all/3.7.0/)
and [medialibrary](https://repo.maven.apache.org/maven2/org/videolan/android/medialibrary-all/0.13.17/)
AARs, Java source JARs, and POMs match their publisher SHA-1 sidecars. Catalog
SHA-256 values were computed from those complete HTTPS downloads. GitLab source
archives were fetched by their verified full commit IDs; their computed pins
still need independent review.

Both patch sets apply without conflicts to their pinned source bases in a
temporary working copy. That check used the host Git version recorded in the
evidence; it was a source audit, not an APK or native build. The original archive
bytes remain unchanged. A final source-restoration and native-build recipe inside
the pinned build environment remains open.

The APK engine strings are `3.0.23-2-228-gb0e7b54f24` for arm64-v8a and
`3.0.23-2-228-g281f05e7d5` for armeabi-v7a. The upstream VLC commit API returned
404 for both short hashes. The publisher script applies patches with `git am`,
which creates local commits. It is therefore plausible that the differing strings
come from those build-local commits; this is an inference, not proof of an exact
source tree or a reproduced binary.

## Notices and remaining work

The published Java source JARs contain 40 and 48 Java files, respectively, and
no C/C++ sources or standalone license documents. They cannot replace native
sources. Their file notices include both GPL-2.0-or-later and LGPL-2.1-or-later;
for example, `RendererDiscoverer.java` in the LibVLC JAR and `EventTools.java` in
the medialibrary JAR carry GPL notices. The publisher POMs name LGPL 2.1, which
does not provide a complete per-file license inventory. Catalog expressions and
review markers preserve that distinction. Original notices and the license
documents in the project archives are retained.

SQLite's [publisher copyright statement](https://www.sqlite.org/copyright.html)
dedicates its deliverable code to the public domain and distinguishes build
scripts with other licenses. The SQLite catalog item retains a marker for those
bundled build-script notices. Native project source archives likewise need a
complete per-file review; collecting an archive is not that review.

Before release:

- Collect the exact enabled VLC contrib source archives, patches, and notices.
  The VLC base archive contains recipes and checksums, not all of their tarballs.
- Complete the Java/Kotlin, Android, and bundled remote-client dependency sources
  and notices. Preserve the matching lockfiles and build scripts.
- Establish the exact ABI toolchain and C++ runtime provenance and their applicable
  source and notice requirements; do not infer them from a library version alone.
- Document and test archive restoration, submodule restoration, patch application,
  and the build controls needed for the selected releases. The source tar archives
  do not carry Git histories expected by some upstream scripts.
- Complete independent pin/license review and the physical Android installation
  and video-language switching checks.

The existing release gates remain in place. This source subset is useful evidence,
and it does not establish complete corresponding-source closure for either APK.

## Repeat the native artifact audit

After `rtk proxy make build-container`, run from the repository root:

```sh
rtk proxy docker run --rm --network=none --platform linux/amd64 \
  --volume "$PWD:/source:ro" --volume "$PWD/cache:/cache:ro" \
  --volume "$PWD/build:/artifacts" --workdir /source --env PYTHONPATH=src \
  --entrypoint /workspace/.venv/bin/python common-knowledge-build:dev \
  tools/audit_vlc_native.py --cache /cache --output /artifacts/vlc-native-bindings.json
```

The audit verifies each cache hash and matches every standard APK native member
by ABI, filename, size, and SHA-256. An unknown member, changed byte, duplicate
archive member, or wrong ABI fails. It explicitly leaves application source
closure and human approvals false.
