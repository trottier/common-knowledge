# Local LLM selection for v0.1

This is packaging research and a startup check. The project has not tuned the models
or evaluated their emergency advice, language quality or suitability for medical use.
The warning comes from `pipelines/llm/settings.yaml` in START, launchers and the page.

Gemma 4 E2B was considered first. Google's [base model card](https://huggingface.co/google/gemma-4-E2B)
states Apache-2.0, a 128K context and support for over 140 languages. The publisher
clarified that its 2.3B effective parameter count satisfies the project's parameter
limit; counting its embeddings does not change the separate 2.5 GB file limit.
The [Google QAT Q4 GGUF](https://huggingface.co/google/gemma-4-E2B-it-qat-q4_0-gguf)
examined is instruction-tuned and 3,349,516,256 bytes. It fails both the untuned-base
requirement and the file limit. No eligible Gemma base GGUF has been pinned here.
This does not establish that no eligible conversion can exist. The v0.4 Gemma plan
is unchanged.

The full-profile alternate is [Qwen3.5-2B-Base](https://huggingface.co/Qwen/Qwen3.5-2B-Base),
Apache-2.0. Its immutable community-published Q4_K_M GGUF is 1,270,808,256 bytes.
The sample uses Qwen3.5-0.8B-Base, 529,297,536 bytes. Both were downloaded over HTTPS
and matched the publishers' Hugging Face LFS SHA-256 values. The catalog pins the
upstream license commits and the conversion repositories separately. GGUF inspection
found Base metadata, qwen35 architecture and a 262,144-token native context in both;
the launchers request 32,768. Tensor counts in the files are 1,881,825,088 and
752,393,024 respectively. These are text-only GGUF files; no vision projector ships.
No claim of coverage for all fifteen editions follows from these metadata checks.

`ck local-llm` rejects an oversized file, unsupported quantization, license mismatch,
missing base provenance, excess parameters or insufficient context. The separate
model file is placed by the capacity plan. It remains universal unless measured
totals require the four variants configured in `fallback_variants`. Unknown sizes
block planning; they never justify dropping a copy or any other content.

The portable [llamafile 0.10.6 thin runner](https://github.com/mozilla-ai/llamafile/releases/tag/0.10.6)
is pinned by the release checksum. Each launcher copies the original executable
to a temporary writable folder and leaves the model on the drive. It binds to
127.0.0.1 with offline mode, a single inference slot and context shifting disabled.
It opens the browser only after its own process reports readiness. The browser
uses local assets and keeps the conversation in memory. START is included with
every request when it fits the conservative context budget. Otherwise the prompt
contains the exact section titles, and the page tells the reader to open START
for instructions. The full English and Spanish START text is available from
local page links in either mode. Failed or canceled turns are not added to history.

[OfflineLLM 5.1.4](https://github.com/jegly/OfflineLLM/releases/tag/v5.1.4) is the
held Android development candidate. Its exact APK/source pins, modern hybrid
verification, local import, custom-prompt controls, and delegated-service limits
are documented in the [adoption handoff](android-local-llm-adoption.md).
Android uses a separate 16K section-index prompt; the laptop stays at 32K, and
the selected models' native-context checks are unchanged. PocketPal and its
complete historical source graph/evidence remain held and `hub_only`.

Outstanding release gates include named model-license sign-off, conversion provenance
review, the complete runner and APK dependency notice inventory, Windows/Mac/Linux
device checks, Android local import with networking off and the manual phone checklist.
The CPU-only startup observed on native ARM Linux is not a substitute for these checks.

A native Mac ARM64 smoke check also started the portable runner with a 32K context,
served the custom page and returned HTTP 200 for English and Spanish requests using
the complete respective START prompts. It requested eight output tokens solely to
check transport. It used `/bin/sh`, suppressed browser opening and changed the test
port to 18085 because an unrelated service occupied 8080. This did not test Finder
double-click opening, a physical USB drive or answer quality.

The bundle carries the original [llamafile Apache notice](https://github.com/mozilla-ai/llamafile/blob/017cdeb4b7217c0fb44cc7b61f44bd8ab2749dd2/LICENSE),
the pinned [llama.cpp component notices](https://github.com/mozilla-ai/llamafile/blob/017cdeb4b7217c0fb44cc7b61f44bd8ab2749dd2/llama.cpp.patches/llamafile-files/common/license.cpp),
the model and selected Android app/native license texts and the [Noto Sans OFL notice](https://github.com/google/fonts/blob/6c1dbe27dcf7d817d4b62cec033ba77fa8e2a5ec/ofl/notosans/OFL.txt).
Project code is [Apache-2.0](../LICENSE); original START text is [CC0](../LICENSE-CONTENT).
These files do not close the outstanding dependency notice inventory.

Run the browser behavior tests with `bun test pipelines/llm/ui/app.test.js`.
Two independent full-profile bundle builds at epoch 1793401527 produced identical
payload hashes and generation manifests: 44,039,478 bytes, manifest SHA-256
`af99947cc4b7e49a9e9c014b3cb1fd5f680bff42fb0c1bd0baeedb238a4276eb`.
This checks the bundle, not a complete drive image.

After the Android import-guide changes, fresh sample and full bundle pairs at
development epoch 1793404800 matched again. The
[repeat receipt](evidence/local-llm-repeat.json) binds the exact container image,
generation manifests, and rehashed payload and intermediate entries in both
builds and their canonical copies. Sample payloads total 44,076,690 bytes; full
payloads total 44,053,192 bytes. The recipe is
`local-llm-v1-cc421817dc563d81834f1b34f7df357c753dd0f989ae3ed4e300a296899b69f6`.
The model remains a separate file. This establishes packaging reproducibility;
model quality, physical devices, source completeness, and human reviews remain
open.

Those repeat results describe the earlier PocketPal-instruction recipe. The
OfflineLLM selection changed settings, source guides, inputs, and the producer.
Its subsequent [fresh sample/full pairs](android-local-llm-repeat.md) now match
at development epoch 1793404800. The refreshed sample payloads total 44,248,498
bytes and full payloads total 44,224,664 bytes; the catalog uses their measured
manifest hashes and recipe. Historical receipts remain intact. No physical
device or model-quality result follows from this packaging repeat.

Run `uv run pytest tests/test_llm.py` inside the pinned build container. New browser
code uses Bun; the atlas retains its documented Node native-module ABI constraint.
