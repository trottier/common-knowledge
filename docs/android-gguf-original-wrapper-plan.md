# Original minimal Android wrapper: pinned build plan

This is a development fallback if an unchanged publisher APK cannot satisfy the
delegated-service policy. No wrapper APK is implemented, compiled, or signed by
this packet. Existing publisher files remain unchanged.

Use the cataloged llama.cpp v0.8.0 source archive at commit
`8642541b255bfb5dc39cd351a178be09013a55d6`. The original Android sample demonstrates
local URI import, but a new framework-only Java Activity and a small original
JNI shim avoid AndroidX's font initializer, TTS, model catalogs, and networking
code. The main wrapper license would be the repository's Apache-2.0; llama.cpp
and selected runtime notices remain separately applicable.

The proposed source files are an original manifest, one Java Activity, one JNI
translation unit, one CMake project, and an original build recipe. The manifest
requests no INTERNET/network permission and disables backup. Use the framework
document picker only when the user taps Import; copy the chosen model to private
storage, verifying its pinned size/hash before loading it. No remote model list,
font request, speech engine, analytics client, or background provider is needed.

The JNI boundary needs only explicit local operations: load/unload, count tokens,
set the project-generated system prompt, generate/cancel, and clear a chat. Use
`llama_model_load_from_file`, `llama_init_from_model`, tokenizer/sampler/decoder
APIs, and supported chat formatting. Reject context overflow and preserve the
system prompt instead of shifting or silently dropping safety text. Render all
warnings/settings from existing configuration. This is intended behavior,
without a model-quality or memory-fit claim.

The exact Gradle8.14.3 distribution checksum and AGP8.13.2 POM were fetched from
their primary publishers. Google repository metadata verifies these proposed
Linux package versions, URLs, sizes, and SHA-1 checksums:

- Android platform36 revision2 and Build Tools36.0.0.
- NDK27.3.13750724, the stable r27d package.
- CMake3.31.6.
- Java17 from the existing pinned build image.

The [evidence](evidence/android-gguf-runner-candidate.json) retains those exact
pins. The large SDK/NDK/Gradle payloads were not downloaded for this plan; their
payload SHA-256 pins and full dependency-verification metadata remain explicit
prerequisites. Do not replace those pending checks with invented hashes.

Use the existing Java17 build image with separate mounted tool/cache directories;
do not edit Dockerfile.build or uv.lock. For the first prototype, build only
arm64 with API33 as the declared minimum, matching the inspected runner class.
Treat additional ABIs and older-platform support as separate tested work.

Build llama.cpp as a library from its original source, with these existing
upstream switches disabled for the CPU-only prototype:

```text
LLAMA_BUILD_COMMON=OFF  LLAMA_BUILD_APP=OFF  LLAMA_BUILD_TOOLS=OFF
LLAMA_BUILD_EXAMPLES=OFF  LLAMA_BUILD_TESTS=OFF  LLAMA_BUILD_SERVER=OFF
LLAMA_BUILD_UI=OFF  LLAMA_CONNECT=OFF  LLAMA_OPENSSL=OFF
LLAMA_LLGUIDANCE=OFF  LLAMA_SUBPROCESS=OFF
GGML_NATIVE=OFF  GGML_BACKEND_DL=OFF  GGML_CPU_ALL_VARIANTS=OFF
GGML_CPU_KLEIDIAI=OFF  GGML_OPENMP=OFF  GGML_LLAMAFILE=OFF
GGML_VULKAN=OFF  GGML_CUDA=OFF  GGML_RPC=OFF
```

This avoids the sample's KleidiAI fetch and optional HTTP/common, Vulkan shader,
and OpenMP toolchains. Use the platform's default baseline architecture rather
than adding a global architecture flag. Include the original notices for all
native files and any packaged C++ runtime; a CPU-only selection does not license
the entire upstream archive automatically.

Before compiling, create a separate original Android build recipe, pin the SDK
archives after publisher-checksum validation, resolve and freeze build-tool
dependencies, and verify offline configuration. Then build **assembleRelease**
with no signing configuration, yielding an unsigned review artifact. Do not
invoke debug builds that create keys, generate a release key, or distribute an
unsigned APK as installable. Signing remains outside this task.

Validate the merged manifest, exact native dependencies/notices, model import,
both selected GGUFs, project prompt/warning flow, overflow/cancel behavior,
installation, and network behavior before selecting or publishing any APK.
