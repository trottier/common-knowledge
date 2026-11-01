# PocketPal 1.22.0 source and shipment audit

The selected PocketPal APK remains **blocked from shipment**. Static source
inspection identifies external initialization requests and purchase-event
reporting, with matching strings in the actual APK bundle. Native source,
SDK rights, and notice review also remain incomplete. No app was installed or
launched, no native code was compiled, and no network traffic was measured.

This November 1, 2026 audit adds fourteen held source candidates in
[the catalog](../catalog/pocketpal_sources.yaml) and an additive source graph.
The [APK catalog](../catalog/apk.yaml) retains the original selection, URL,
version, size, checksum, signer, source URL, and prior review marker. It adds
explicit shipment and named legal-review holds. The existing PocketPal MIT
license text in `catalog/llm.yaml` remains an original app notice; it does not
clear every component of the APK. No frozen LLM producer fields changed.

[Machine-readable evidence](evidence/pocketpal-source-audit-2026-11-01.json)
records the original artifacts, source-file hashes, line references, native
comparisons, permissions, and bundle offsets. Cargo remains in the ignored,
SHA-256-keyed cache. Computed pins and per-file compliance still need human
review; publisher license declarations are not whole-package approval.

## Exact selected artifact and provenance boundary

The [publisher release](https://github.com/a-ghorbani/pocketpal-ai/releases/tag/v1.22.0)
names the selected 275,953,055-byte APK. Its published SHA-256 matches the cached
file, and `apksigner verify` confirms the catalog's certificate SHA-256. The
release tag resolves to `8932367e9f4a373945993ae0a472c8768d5c0578`; its source
archive is now pinned. However, the APK's embedded version-control metadata
reports `NO_SUPPORTED_VCS_FOUND`. This is release/tag association, not an
embedded commit match or a reproducible source build.

The APK contains **85 ELF files**: 80 under `lib/`, for ARM64 and x86-64, and
five Hexagon DSP libraries under `assets/ggml-hexagon/`. Native inventory must
include these assets. All sixteen llama.rn core/JNI libraries define the
corresponding v3 patch markers from the app's original source patch. The
Hexagon variant also defines its backend registration symbols. These are
bounded static correspondence checks, not execution or accelerator tests.

## Concrete external calls: shipment blockers

The source's [persistence callback](https://github.com/a-ghorbani/pocketpal-ai/blob/8932367e9f4a373945993ae0a472c8768d5c0578/src/store/ModelStore.ts#L304)
starts model-store initialization. That
[initialization calls the online rules upgrade](https://github.com/a-ghorbani/pocketpal-ai/blob/8932367e9f4a373945993ae0a472c8768d5c0578/src/store/ModelStore.ts#L775),
which [calls `fetchRules`](https://github.com/a-ghorbani/pocketpal-ai/blob/8932367e9f4a373945993ae0a472c8768d5c0578/src/store/ModelStore.ts#L991).
The [request implementation](https://github.com/a-ghorbani/pocketpal-ai/blob/8932367e9f4a373945993ae0a472c8768d5c0578/src/services/deviceRules/rules.ts#L18)
uses a [mutable jsDelivr `@main` URL](https://github.com/a-ghorbani/pocketpal-ai/blob/8932367e9f4a373945993ae0a472c8768d5c0578/src/services/deviceRules/rulesUrls.ts#L3).
It falls back to bundled presets on failure; that fallback does not remove
the external call from the artifact.

The [purchase-event transport](https://github.com/a-ghorbani/pocketpal-ai/blob/8932367e9f4a373945993ae0a472c8768d5c0578/src/services/palshub/palEvents.ts#L3)
posts event names to `/api/mobile/pals/<id>/event`.
[Purchase-store call sites](https://github.com/a-ghorbani/pocketpal-ai/blob/8932367e9f4a373945993ae0a472c8768d5c0578/src/store/PurchaseStore.ts#L1323)
include buy taps, cancellation, and errors; the
[production dependency](https://github.com/a-ghorbani/pocketpal-ai/blob/8932367e9f4a373945993ae0a472c8768d5c0578/src/store/PurchaseStore.ts#L1836)
selects that transport. These event-reporting paths require resolution under
the project's no-network and no-telemetry rules before shipment.

The APK's actual `assets/index.android.bundle` contains the device-rules URL,
event path fragments, and all three event names at recorded byte offsets.
Its decoded binary manifest declares INTERNET permission. These observations
corroborate source paths; they do not establish which calls ran or transmitted
data. Do not remove the hold merely because local inference may work offline.

Separately, [benchmark sharing has a consent dialog](https://github.com/a-ghorbani/pocketpal-ai/blob/8932367e9f4a373945993ae0a472c8768d5c0578/src/screens/BenchmarkScreen/BenchmarkScreen.tsx#L260).
The [App Check helper](https://github.com/a-ghorbani/pocketpal-ai/blob/8932367e9f4a373945993ae0a472c8768d5c0578/src/utils/fb.ts#L39)
configures Play Integrity and token refresh when initialized. Firebase and
ML Kit initialization components also occur in the APK manifest. SDK presence
does not by itself establish telemetry. This audit neither contacted these
services nor extracted live service credentials.

## Exact native/package inputs, with limited comparisons

Seven original registry archives match both their publishers' SHA-1/SHA-512
metadata and the app's exact `yarn.lock` integrity values:

| Component | Locked version |
| --- | --- |
| llama.rn | 0.13.0-rc.9 |
| React Native | 0.87.1 |
| whisper.rn | 0.7.4 |
| `@pocketpalai/react-native-speech` | 2.8.2 |
| `@pocketpalai/react-native-speech-phonon` | 0.1.3 |
| ONNX Runtime React Native | 1.24.3 |
| Nitro Modules | 0.37.1 |

The [app manifest](https://github.com/a-ghorbani/pocketpal-ai/blob/8932367e9f4a373945993ae0a472c8768d5c0578/package.json)
alone is insufficient: its ONNX range begins at 1.23.2, while the lock selects
1.24.3. Original llama.rn and ONNX patches are in the pinned app archive.
The [binding's vendor manifest](https://github.com/mybigday/llama.rn/blob/27783c86cea93ac534fba303d9be5cf335d2e945/vendor/VERSIONS)
pins llama.cpp to `8642541b255bfb5dc39cd351a178be09013a55d6`, alongside codec.cpp
and Khronos inputs. No latest upstream revision was substituted.

| Comparison with selected APK | Result |
| --- | --- |
| React Native 0.87.1 release AAR | Four native files match exactly; its two C++ runtime files differ |
| Hermes 250829098.0.17 release AAR | Six native files match exactly |
| llama.rn registry tarball | Five DSP assets match exactly |
| ONNX Runtime 1.24.3 AAR | Two native files share build IDs and allocated-section hashes; file bytes differ |
| Phonon native Android ZIP | ARM64 runtime shares allocated-section hashes; file bytes differ |

The ONNX and Phonon differences involve section-name tables; their complete
files are not byte-identical. The React Native C++ runtime differences include
build IDs and compiler comments. None of these observations replaces an exact
native build/dependency record. The React Native and Hermes source JARs contain
no C/C++ source. The catalog therefore also records preferred source/package
inputs, with their remaining dependency and notice reviews held open.

## Phonon: actual native license and source evidence

The [native binary release](https://github.com/a-ghorbani/react-native-speech/releases/tag/phonon-bin-v0.4.0-r2)
matches both its publisher SHA-256 and the package's `phonon.lock.json`. Its
ZIP contains native-specific dependency notices, build metadata, and **both
MIT and Apache license texts**. Those texts and its public FFI header match
the pinned upstream source byte for byte. The upstream
[workspace declaration](https://github.com/gradium-ai/xn-ptts/blob/f07d7952db0c6127d5e4bc3f41c82b3304b6b5aa/Cargo.toml)
states `MIT OR Apache-2.0`. This is evidence about the native component,
independent of the wrapper's MIT declaration.

The binary producer tag resolves to
`f2fc556d9aa6b92dd617fd11f96f3a51ef9c8861`, separately pinned from the later
package source. Its
[Android recipe](https://github.com/a-ghorbani/react-native-speech/blob/f2fc556d9aa6b92dd617fd11f96f3a51ef9c8861/packages/react-native-speech-phonon/scripts/build-android.sh)
requires the exact clean upstream commit and uses a locked Cargo build.
Published BUILDINFO records Rust, cargo-ndk, NDK, target flags, and an epoch;
this project did not repeat that build. The upstream workspace lock has 563
packages, including 556 registry entries. That is not the Android linked-crate
count: target/frontend selection and full dependency-source review remain open.

The app source's 65-section JSON reconstructs the selected package's combined
native notice file exactly. The binary ZIP also carries a separate Android
notice file. Neither comparison verifies notice display on a phone. No
Phonon checkpoint files appear in the inspected APK model-file/asset listing;
the wrapper's discussion of separately obtained noncommercial models does not
make its native-code license noncommercial. No model redistribution grant or
whole-APK approval follows from this finding.

## Remaining source, rights, and review work

The [Hexagon setup recipe](https://github.com/a-ghorbani/pocketpal-ai/blob/8932367e9f4a373945993ae0a472c8768d5c0578/.github/actions/setup-hexagon-sdk/action.yml)
identifies a third-party SDK repackaging, not Qualcomm's own distribution.
Its content digests identify an input; they do not establish redistribution
rights. No Hexagon SDK was downloaded or compiled in this audit. Google SDK components
and other native libraries likewise need exact terms, corresponding notices,
and any applicable source obligations reviewed.

The fourteen catalog nodes are a verified subset for provenance and rebuild
work. They are not the complete NPM, Maven, Rust, Android runtime, font, asset,
or toolchain graph. Complete the target-specific dependency and per-file
license inventories, resolve native build correspondence, and satisfy the
known network/event shipment blockers before any release. All source nodes
remain hub-only and unreviewed; no named legal or content approvals were set.
