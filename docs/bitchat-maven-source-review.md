# bitchat Maven dependency source checkpoint

The pinned bitchat 2.2.0 source archive contains 194 coordinates assigned to
`releaseCompileClasspath` or `releaseRuntimeClasspath` in `app/gradle.lockfile`.
This audit covers the 52 coordinates outside AndroidX. The other 142 coordinates
remain outside this checkpoint. A locked coordinate is not a claim that every
class from that artifact survives release shrinking or runs on a device.
The [evidence record](evidence/bitchat-maven-sources.json) identifies the exact
application, source archive, lockfile hash, configurations, and publisher URLs.

## Source archive candidates

`catalog/bitchat_maven_sources.yaml` pins 35 unchanged publisher source JARs,
totaling 15,277,651 bytes. All pass ZIP integrity checks and contain source files.
Nineteen match publisher SHA-256 files; sixteen match publisher SHA-1 files and
have separately computed, still unreviewed SHA-256 pins. Every source record
links its actual publisher checksum file.

The publisher POMs declare Apache-2.0 for 32 archives and BSD-3-Clause for two.
The remaining archive is Bouncy Castle; its publisher says its license is read
as [the MIT license](https://www.bouncycastle.org/licence.html). Direct and
inherited POM declarations are retained in the evidence record. Original source
headers and notices remain in the archives. A source JAR can omit build scripts,
native dependencies, or other files needed for complete corresponding source,
so none of these entries grants application source-closure approval.

The [linkage proposal](evidence/bitchat-maven-source-links.json) lists the 35 IDs
to append to `bitchat_android_source.inputs`, preserving existing inputs. It
also records the expected parent archive hash. The two SDK audit inputs below
must stay outside that corresponding-source list.
The catalog applies this proposal alongside the existing Rust inputs and the
[separate AndroidX source checkpoint](bitchat-androidx-source-review.md).

## Specific unresolved SDK obligations

The conventional publisher source-JAR endpoints returned HTTP 404 for fourteen
AAR coordinates in this subset: three Android Data Transport artifacts, five
Google Play Services artifacts, five ML Kit artifacts, and one ODML artifact.
The evidence lists each attempted URL, response, and original POM. This does
not establish that their sources are unavailable from every upstream location.
Three further 404s belong to POM-only Kotlin common/BOM coordinates and are
separated from those fourteen AARs.

Google's original `barcode-scanning:17.3.0` AAR has SHA-256
`64c5cf48bb94b6c54f2c785c660640a7d167aff6ad72bc2c920706dc4187b79a`,
matching its publisher checksum file. All four `libbarhopper_v3.so` files in
that AAR are byte-identical to the copies in the pinned bitchat APK. Its
[publisher POM](https://dl.google.com/dl/android/maven2/com/google/mlkit/barcode-scanning/17.3.0/barcode-scanning-17.3.0.pom)
declares the ML Kit Terms of Service. The dependency is therefore present in
the APK's bytes; it is not merely an unused version-catalog alias.

Google's terms state that ML Kit APIs “send metrics about the performance and
utilization of the APIs in your app” and may contact Google for updates. They
also restrict source extraction and reverse engineering, subject to applicable
law. These are concrete issues for this project's no-telemetry rule and source
review. See [ML Kit Terms & Privacy](https://developers.google.com/ml-kit/terms).
No device traffic was measured, and this audit does not claim that the pinned
APK emitted metrics or that every SDK code path is invoked.

`catalog/bitchat_dependency_audits.yaml` records the two original Google AARs
used for this comparison as `hub_only` audit inputs with unresolved rights
markers. They are not drive content or source-archive substitutes. The APK,
its placement, and all human and legal review statuses remain unchanged.

The application catalog records the unresolved bundled SDK terms and retains
its named legal-review requirement. Remaining work includes native and Java
build inputs and notices, exact binary/source correspondence, SDK term compatibility, a measured
offline and no-telemetry device check, and named human review. The source and
rights gates remain unresolved.
