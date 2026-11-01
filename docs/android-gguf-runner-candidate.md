# Android local-GGUF runner candidate

OfflineLLM 5.1.4 is a concrete held development candidate for replacing
PocketPal. Its original publisher APK matches the release SHA-256, passes modern
legacy/hybrid signature verification, and declares no INTERNET or network-state
permission in its merged manifest. It supports local model import and a custom
system prompt. No app selection or approval changes in this packet.

| Route | Verified source facts | Remaining limits |
| --- | --- | --- |
| OfflineLLM 5.1.4 | Original 51,249,006-byte APK; exact app commit `a9a62d28841b8dd6fdb44e94bf4285c4b6d7a760`; exact llama.cpp submodule `60eeeb6082c1126bb8bc72902c83123cd056811b`; Apache-2.0 app and MIT native declarations | Android 13+/arm64; full dependency notices and native correspondence remain open; delegated emoji-font and speech services need resolution/testing |
| Official llama.cpp v0.8.0 Android sample | Exact commit `8642541b255bfb5dc39cd351a178be09013a55d6`; local SAF import; app/library manifests omit INTERNET; qwen35 implementation present | No APK in that release's assets; sample enables cloud backup, does not set the CK prompt, and shifts context; app/library require API33 and pinned NDK29 beta1 |
| Original minimal CK wrapper | A concrete build plan can consume the unchanged pinned llama.cpp source and only framework UI/C APIs | Proposed code, not an APK or tested device result; see the separate build plan |

The [source and verification evidence](evidence/android-gguf-runner-candidate.json)
records the exact artifacts, source-file hashes, merged manifest, native library
hashes, model metadata, current tool bootstrap, and proposal outputs. All added
catalog items are `hub_only` and retain their review holds.

## Model and source linkage

Both selected cached GGUF files identify `qwen35`, Q4_K_M, Base provenance, and
a 262,144-token native context. Both contain the same chat-template bytes.
The exact OfflineLLM submodule registers qwen35, constructs its model class,
and contains its tensor/graph implementation. The APK's native library also
contains the architecture identifier. This is source/static compatibility
evidence; the models have not been loaded or evaluated on a phone in this audit.

The app source imports a user-selected file through `ContentResolver` into
private storage. Its native loader calls `llama_model_load_from_file` and does
not link llama-common's HTTP/download helpers. CPU mode explicitly limits
devices selected for model loading. The app's default conversation formatter
and context handling differ from the laptop UI; no exact behavioral parity
claim is made.

The publisher's successful
[release workflow](https://github.com/jegly/OfflineLLM/actions/runs/41184355644)
records NDK27.2.12479018, Vulkan-Headers v1.4.367, and SPIRV-Headers
vulkan-sdk-1.4.363.0. The exact header source archives are pinned and linked.
Vulkan-Headers declares Apache/MIT file grants; SPIRV-Headers also carries
CC-BY-4.0 documentation, which is retained in its catalog license expression.
The release's native graphics-path library matches the previously audited
graphics-path1.0.1 AAR byte for byte. Relevant existing source pins are reused.

The complete resolved Maven runtime graph, remaining OpenMP/NDK inputs,
automatically selected CMake version, native build correspondence, and final
notice delivery remain open. Source availability and permissive main licenses
do not establish complete application source or notice closure.

## Network restriction and delegated services

Google aapt2 independently confirms the merged APK has only biometric,
legacy-storage, fingerprint, and local receiver permissions, with backup
disabled. App/native source inspection found no direct HTTP/download/analytics
initialization calls in the inspected application paths. No app was installed
or run, and no traffic capture was performed.

There are two concrete delegated paths. The merged manifest registers
EmojiCompatInitializer1.4.0, whose exact pinned source requests emoji fonts from
a system-installed provider after first resume. ChatViewModel also constructs
the phone's TextToSpeech engine. Their presence does not prove an external
network request, and the app's missing INTERNET permission does not constrain
every separate system service. These are specific remaining policy/device
checks. The candidate is not described as having proven zero external traffic.

The original-wrapper plan avoids those dependencies entirely instead of
modifying any publisher file.

## Modern verifier: reproducible fetch and offline checks

The frozen build image's older apksigner reports an unknown `0xbf940529`
attribute. That result is insufficient for this candidate. Android documents
that attribute as part of v3.2 hybrid stripping protection, with hybrid
verification beginning at API37. [AOSP signing documentation](https://source.android.com/docs/security/features/apksigning/v3-2)

The new additive adapter uses the original apksigner JAR from Google Build
Tools37. Its exact archive and member hashes/sizes are cataloged. It verifies
without min/max-SDK overrides and requires the catalog legacy certificate,
both pinned hybrid certificates, and verified v3/v3.2 schemes. Warnings or
verification failures are errors; it never falls back to API36-only checks.

The observed legacy signer is RSA for API33–36. API37 verification additionally
passes the new classical EC and ML-DSA hybrid signers and their lineage checks.
All three certificate hashes and the tool's exact SDK-range output are retained
in the evidence and verifier policy. The tools generated no keys or signatures.

The archive is cataloged as `LicenseRef-Android-SDK`; it is not labeled Apache
merely because apksig is Apache-2.0. The original JAR has a separately scoped
component license proof. SDK/component terms, use, and notice review remain
explicit holds. The SDK archive and tool stay in build caches and are never
drive/release payloads. No SDK license-acceptance command or approval flag is
set. Google's terms distinguish SDK use from open-source component licensing.
[SDK terms](https://developer.android.com/studio/terms)

The separate bootstrap downloads only a pinned, size-bounded Google Build Tools
archive with a `hub_only` build destination. It changes no generic license
allowlist. It copies only the original, size/hash-checked JAR member. Normal
content fetch still rejects an SDK license as redistributable content.

Run the additive route in the locked Java17 build environment:

```sh
rtk proxy uv run --locked python tools/verify_android_candidate.py \
  --cache cache --tool-cache cache/build-tools/apksigner \
  --output build/offlinellm-verification.json
```

It uses the existing `fetch(..., format_check=...)` hook, so checksum checks and
quarantine behavior remain active. A real empty-cache run downloaded both the
SDK archive and APK, extracted the verifier, and passed all signatures using
Java17.0.21. A second run with networking disabled produced an identical report.
No manually populated cache was required for that bootstrap test.

Before adoption, wire this callback for the selected APK fetch/build path;
ordinary PATH apksigner remains unchanged in this packet. Retain the SDK's
build-only restrictions and review holds rather than publishing its archive.

## Separate grounding/how-to proposal

The candidate UI caps context at 16,384. The new proposal configuration and
renderer live outside `pipelines/llm`, so that producer's recursive fingerprint
is unchanged. The renderer validates the current 71 frozen bundle against its
current catalog pin, then reuses the existing system-prompt policy at the
smaller candidate context. English and Spanish both receive complete section
indexes when full START text does not fit; complete reference text remains in
the verified source bundle. Existing warning/settings values are read from
their single shared configuration.

The existing laptop configuration enforces a 32K runner context. The Android
renderer uses an explicit, separately validated proposal contract capped at
this APK's UI limit; it does not bypass validation or change that laptop rule.
The models' native-context metadata remains above the selection criterion.
Accepting a smaller Android running context is still an adoption decision.

```sh
rtk proxy uv run --locked python tools/prepare_android_llm_candidate.py \
  --bundle build/generated/local_llm_sample --bundle-id local_llm_sample \
  --output build/android-llm-companion-review
```

This produces proposed prompt text, draft how-to Markdown, and a grounding
record. The source confirms **Import GGUF Model**, **System Prompt → Custom**,
and the multiline custom-prompt field. Sliders quantize some values, so exact
sampling parity remains unproven. Clipboard behavior and complete prompt
application need device checks. The how-to must be reviewed and rendered to
phone/print PDFs before placement.

Adoption is a separate coordinated change: retain PocketPal and its source
graph as a held historical candidate, move its APK to `hub_only`, place the new
APK/licenses, wire modern verification, update all instructions, and rebuild
affected generated items with fresh measured pins. This packet changes none
of the current selected settings, frozen bundles, or producer inputs.
