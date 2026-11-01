# bitchat AndroidX source checkpoint

This checkpoint covers all 142 AndroidX coordinates assigned to the pinned
bitchat 2.2.0 app's release compile or runtime classpaths. Every publisher POM's
group, artifact, and version matches its locked coordinate. It complements the
[52-coordinate Maven audit](bitchat-maven-source-review.md); neither checkpoint
claims that every locked class survives shrinking or runs on a device.

The [evidence record](evidence/bitchat-androidx-sources.json) binds the results to
the application, application source, Gradle lockfile, original publisher files,
checksums, configurations, and POM license declarations.

## Original publisher archives

`catalog/bitchat_androidx_sources.yaml` pins 141 unchanged source JARs from
Google's Android Maven repository, totaling 40,054,763 bytes. All pass ZIP
integrity checks. Of these, 126 match publisher SHA-256 files, and 15 match
publisher SHA-1 files with separately computed, still unreviewed SHA-256 pins.
Every entry links its actual checksum file and license-declaring POM.

The source archive contents are distinguished explicitly:

| Contents | Archives | Meaning |
| --- | ---: | --- |
| Source files present | 129 | Source candidates; build and native source completeness remain unconfirmed |
| Only `META-INF` manifests and license files | 12 | Metadata/notices only; not implementation source |
| Compose BOM `2026.06.01` | No source JAR | Publisher POM-only coordinate; conventional source-JAR endpoint returned HTTP 404 |

The twelve metadata/notices-only archives are listed with every contained path
in the evidence record. They include several KTX compatibility artifacts and
`androidx.tracing:tracing:1.3.0`. This audit does not infer that their binaries
are empty or that all implementation/variant forwarding has been resolved.
Those checks remain explicit catalog review markers.

The POMs declare Apache-2.0 for 140 source archives. Camera Core `1.6.1` declares
both Apache-2.0 and BSD-3-Clause. These are publisher declarations, not a complete
per-file rights audit. The archives retain their original headers and notices.
No third-party payload is committed to Git.

The [linkage proposal](evidence/bitchat-androidx-source-links.json) lists 141
source IDs to append to `bitchat_android_source.inputs`. It checks the parent
source hash and preserves all existing Rust and Maven inputs. The two native
audit AARs below must stay outside the corresponding-source graph.
The catalog applies this proposal without linking either audit AAR.

## Native source gaps identified by exact bytes

Two original AndroidX AARs identify twelve native libraries present in the
pinned APK. Their publisher checksums and every library's hash are recorded in
the evidence:

| Publisher artifact | Original AAR SHA-256 | APK libraries matched |
| --- | --- | ---: |
| [Camera Core `1.6.1` POM](https://dl.google.com/dl/android/maven2/androidx/camera/camera-core/1.6.1/camera-core-1.6.1.pom) | `a36f1c323851b51215ba476640e1eb4153882b0c368c0376e9fb905e689df84a` | 8: image-processing and surface JNI, across four ABIs |
| [Graphics Path `1.0.1` POM](https://dl.google.com/dl/android/maven2/androidx/graphics/graphics-path/1.0.1/graphics-path-1.0.1.pom) | `8ca4032b6d79b351f0b59ad4b580eddbb9423e1652f7c958830687f1eee2ec03` | 4: graphics-path JNI, across four ABIs |

Neither corresponding source JAR contains C, C++, assembly, or header files.
Those JARs therefore do not supply the native source set for these matching
libraries. Exact upstream native sources, external dependencies, build scripts,
and per-file notices still need to be collected and reviewed. This checkpoint
does not claim an application rebuild or complete corresponding source.

`catalog/bitchat_androidx_audits.yaml` pins the two original AARs as `hub_only`
audit inputs. They are not drive content or source substitutes. APK bytes,
placement, and human and legal review statuses remain unchanged.
