# Android local LLM development selection

OfflineLLM 5.1.4 is now the selected **held development candidate** for Android.
This selection grants no source, legal, device, or release approval. Its exact
APK, app commit, native submodule, signatures, and inspected controls are bound
in the earlier [research receipt](evidence/android-gguf-runner-candidate.json).
That receipt describes the research baseline; its statement that selection and
frozen producers were unchanged applies to that earlier packet.

PocketPal remains in the catalog as a held `hub_only` historical candidate.
Its source archive, dependency graph, network-init/event evidence, notices,
and all review holds remain intact. No third-party bytes are changed.

## Settings, instructions, and grounding

`pipelines/llm/settings.yaml` holds the Android APK ID, filename, supported
Android/ABI bounds, CPU-only choice, and 16,384-token running context. Laptop
launchers still use their unchanged 32,768-token setting. The selected GGUFs'
native-context criterion remains at least 32K; both inspected files report
262,144 tokens. The Android UI limit does not relax the model criterion.

The English guide remains draft; the Spanish guide remains an unreviewed
machine translation with an updated English-body hash. Both read numerical
settings and warnings from shared configuration. The exact publisher Settings,
import, chat, and build source files are cited at their release commit. Guide
steps retain the publisher's English control labels, including **Import GGUF
Model**, **Use**, **GPU Acceleration (Vulkan)**, **Custom System Prompt**, and
**New Chat**. The Temperature instruction targets the displayed value; the
slider's quantization does not establish exact laptop sampling parity.

Fresh `ck local-llm` output will contain separate `android/system-en.txt` and
`android/system-es.txt` files, plus an Android settings/grounding record. These
prompts always contain the complete START section index, explicitly say that
full instructions are absent, and preserve the warning and cards-win policy.
The byte budget subtracts output, context, and message reserves, and rejects an
oversized index rather than truncating it. Laptop prompts remain separate in
`ui/`; they keep their existing full-text-or-index policy.

The generator will copy both languages' phone and print how-to PDFs beside the
APK in `android/`, while retaining their root copies. Its recorded inputs now
include the selected APK and the original app/native license texts. It also
records `src/ck/config.py` in its producer fingerprint so the validated Android
context contract is part of the recipe.

## Verification and build-only tools

CLI fetches, preparation fetches, and assembly all route this selected APK
through the pinned modern verifier. A selected app ID lacking an explicit
modern policy fails rather than falling back to the older PATH tool. The
existing per-item signer and v3/v3.2 scheme requirements remain enforced.

Assembly without `--fetch` requires both the unchanged APK and SDK archive in
cache; a missing or changed verifier input fails before network access. The
original JAR may be restored from that verified archive. Successful audits bind
the APK, JAR, SDK archive, and Build Tools version; assembly includes that tool
provenance in `VERIFY.TXT`. The SDK archive/JAR remain build inputs and never
become drive or release payloads. SDK terms, component notices, and existing
review holds are unchanged. No agreement is accepted, and no key is generated.

The [adoption receipt](evidence/android-local-llm-adoption.json) records a real
normal CLI fetch with container networking disabled, its complete modern
signature report, source hashes, and the targeted test scope. No app was run.

## Fresh build handoff

No replacement bundle was built for this patch, and the existing 71/54 build
directories remain untouched. The two generated catalog entries now carry
explicit pending size/hash/recipe markers and updated inputs. This prevents
assembling the newly selected APK beside stale PocketPal instructions.
The previous [repeat receipt](evidence/local-llm-repeat.json) remains historical
evidence for its original recipe, not proof of the changed producer.

After resources are allocated, build each profile into a **new** directory in
the locked build environment, repeat cleanly, compare actual manifests and
payloads, and replace the pending pins with measured results. Then regenerate
catalog/review reports and verify preparation, assembly, Android guide links,
and all selected inputs. Do not relabel the old bundle or reuse its hash.

## Remaining concrete holds

The app UID's merged manifest has no INTERNET permission, and backup is
disabled. EmojiCompat still requests fonts through an installed provider, and
the app initializes the platform TextToSpeech engine. These delegated paths do
not establish observed traffic, and they are not a zero-traffic guarantee.
The guides require text use without downloaded fonts or voices and leave
read-aloud off; physical checks must establish that this works.

Complete runtime dependency notices, native/toolchain correspondence,
source-pin review, supported-device import/memory behavior, custom-prompt
application, overflow behavior, offline traffic capture, and the manual phone
checklist remain open. No model-quality, emergency-suitability, or release
claim follows from this development selection.
