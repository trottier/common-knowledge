# Briar 1.5.24 dependency source evidence

This packet pins 44 original publisher source archives, totaling 91,885,553
bytes, for the existing Briar 1.5.24 selection. It adds 42 Java/Kotlin source
JARs and the publisher's Tor and Lyrebird source bundles. It leaves application
corresponding-source closure and redistribution review open.

The [publisher repository](https://briarproject.org/fdroid/repo/) identifies its
packages as original-developer official binaries. Its `index-v1.jar` entry for
version code 10524 matches the catalog's APK size, SHA-256, and signing certificate.
That entry has no corresponding-source bundle field. The existing source archive
pins commit `fbfebc4242f09e996a867de7988683628d426534`.

The [machine-readable evidence](evidence/briar-sources.json) records source URLs,
archive hashes, publisher checksums, POM license declarations, inherited license
proofs, source counts, original build-file hashes, and native APK comparisons.
The catalog now applies the [additive linkage proposal](evidence/briar-source-links.json):
the application source has 45 direct inputs, retaining Mailbox and adding these
44 archives. The release-source walk reaches 46 source archives including the
application itself, and excludes both native binary audit JARs.
The [integration receipt](evidence/android-source-graph-integration.json) records
independent cache/archive checks and repeats all eight native APK comparisons.
All 642 existing bitchat source inputs remain unchanged. No payload is committed
to Git; verified bytes are cached by SHA-256. Full corresponding-source closure,
human pin review, and legal approval remain open.

## Bounded Java source set

The packet covers 38 distinct main `api`/`implementation` coordinates declared
by the Android application and its compiled Briar/Bramble modules. It also pins
the separately selected, witness-pinned JTorCtl 0.5 helper, the emoji 0.9.0 base
dependency, and two Kotlin transitives explicitly declared by the
`kotlin-stdlib-jdk8:1.9.25` POM. Tests, screenshot variants, annotation processors,
and desktop/headless modules are outside this subset.

The publisher's `witness.gradle` lists contain artifacts from several Gradle
configurations. They are not release dependency lockfiles. This packet does not
label every witness entry as shipped, resolve version conflict selection, or
claim to contain the full release dependency graph. In particular, Kotlin,
AndroidX, Jackson, and other transitive graphs still need release resolution.

All 42 Java source JARs pass ZIP integrity checks. Twenty-one have matching
publisher SHA-256 checksums, and 21 have matching publisher SHA-1 checksums plus
locally computed SHA-256 pins. Human pin review remains open. The two Kotlin
`jdk7`/`jdk8` source JARs contain only `module-info.java`; their implementation
sources are not represented by those two archives. The separately pinned
`kotlin-stdlib:1.9.25` JAR does contain implementation sources.

The ordinary `emoji-google-0.9.0-sources.jar` URL returns 404. Its
[publisher Gradle metadata](https://repo.maven.apache.org/maven2/com/vanniktech/emoji-google/0.9.0/emoji-google-0.9.0.module)
instead declares debug and release source classifiers. The packet pins the
published `release-sources.jar` for both `emoji-google` and `emoji`; it does not
mistake the POM packaging for a source-free BOM.

Bouncy Castle's declared coordinate is `bcprov-jdk15to18:1.82`; its original
source JAR is pinned. An older Bouncy Castle artifact in the broader witness
list is not silently classified as part of the release.

## Native byte correspondence and publisher recipes

The APK contains eight `.so` files: Tor and Lyrebird for four ABIs. Every one
matches the corresponding entry of the publisher's binary JAR byte for byte.
The JAR hashes also match the original `bramble-android/witness.gradle` pins.
This establishes binary identity, not a source rebuild.

| Publisher source bundle | Bytes | Bundled source evidence |
| --- | ---: | --- |
| `org.briarproject:tor-android:0.4.9.15` | 71,251,198 | Tor 0.4.9.15, OpenSSL 3.5.9, libevent 2.1.13-stable, zlib 1.3.2, and the original Android Makefile |
| `org.briarproject:lyrebird-android:0.6.2` | 8,105,447 | Original Lyrebird sources, `go.mod`, `go.sum`, `vendor/modules.txt`, vendored dependencies, and Makefile |

The exact publisher
[Tor recipe configuration](https://code.briarproject.org/api/v4/projects/briar%2Ftor-reproducer/repository/files/tor-versions.json/raw?ref=5cf61b3abe6a67f1eba34ca62928b87a2e318d3d)
at commit `5cf61b3abe6a67f1eba34ca62928b87a2e318d3d` identifies the same
component versions and NDK revision `29.0.14206865`. The source bundle's
Makefile specifies that NDK revision and per-ABI Android builds.

The exact publisher
[Lyrebird recipe configuration](https://code.briarproject.org/api/v4/projects/98/repository/files/versions.json/raw?ref=c2b43017ffe9ab16896784febc30ddc162899e48)
at commit `c2b43017ffe9ab16896784febc30ddc162899e48` selects upstream commit
`a74149c066d0269326bd49900218744f4d0890fb`, Go `go1.22.12`, and NDK revision
`29.0.14206865`. The branch name includes `ndk-28`, but its actual configuration
selects NDK r29. Current default-branch configuration only described Lyrebird
0.5.0 when inspected; it is not substituted for the exact 0.6.2 recipe.

Recipe configuration response hashes and publisher toolchain hashes are retained
as evidence. Full recipe repositories and toolchain archives are not new catalog
pins in this packet. No native build or APK reproduction was run.

## License and source obligations still open

The native POMs declare BSD licensing, but their complete source bundles carry
additional licenses. The catalog deliberately retains VERIFY markers for the
full inventory rather than treating the POM declaration as sufficient.

- Tor's bundle contains OpenSSL's Apache-2.0 license, zlib's license, and Tor/
  libevent license files with additional upstream terms. Retain original files,
  enumerate per-file grants and notices, and verify binary notice delivery.
- Lyrebird contains BSD notices and GPL-3.0-or-later headers in
  `transports/meeklite/transport.go` and `internal/x25519ell2/x25519ell2.go`,
  as well as its vendored dependency licenses. The exact uTLS replacement in
  `go.mod` must remain part of the source and recipe audit.
- H2's POM offers MPL-2.0 or EPL-1.0. Panic and weupnp carry LGPL obligations.
  JDOM source headers impose binary notice and naming conditions; they are not
  silently classified as ordinary BSD-3-Clause. Glide's combined declarations
  and Briar helpers' GPL version grants need complete source/notice review.
- Source JARs commonly omit original build systems, resources, and license
  files. Obtain the complete required upstream build/source material, resolve
  the actual release graph, bind selected Java binaries to its versions, and
  check generated code and resource inputs. The app source includes a
  reproduction-script reference; its exact production recipe remains to pin.
- Pin complete native recipe repositories and required toolchain/source inputs,
  then reproduce the native binaries and the APK. Retain publisher originals
  without modifying third-party files.
- Complete source pins, attribution and license delivery, human/legal review,
  offline phone tests, and the project's release gates remain required. Neither
  successful downloads nor matching native bytes close those gates.
