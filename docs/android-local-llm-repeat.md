# Android local LLM bundle repeat

Two fresh sample builds and two fresh full builds now match after the held
OfflineLLM development selection. The
[measured receipt](evidence/android-local-llm-repeat.json) records every actual
file, intermediate, container limit, and canonical copy.

| Profile | Placed bytes | Generation-manifest SHA-256 |
| --- | ---: | --- |
| sample | 44,248,498 | `9d4c8380a1b5059ee8853b875e42f0b7e6c80239b7c52a902525c3bd369eccd1` |
| full | 44,224,664 | `8079a5377ad2744927a31126609cd8e4677a29f577cddba1fffb42ef4d31f4d5` |

The frozen producer commit is
`ba88964b7ad0e2eb4c6a3ba01227ed7ac7e356f7`. All four runs report recipe
`local-llm-v1-66574b8c58a01e9f04549f83477b10836ffe723426a743347785d6135e8447f2`.
The receipt captures hashes of its 63 recipe files and the frozen catalog.
The source checkout remained unchanged throughout the runs.

Each fresh Linux amd64 container used image
`sha256:c9792c3f92d4c2bb4a532aab4b5528e7aa9998d1314fcf47a16d72353cd28d52`,
one CPU, a 1 GiB memory limit with no additional swap allowance, networking
disabled, read-only source/cache mounts, and explicit development epoch
`1793404800`. The four builds ran serially. Their actual Docker inspections
show exit code zero and no OOM termination. These development measurements do
not set the release epoch.

Independent verification in the same pinned environment rehashed all 41 files
in each output: 35 placed payloads, four audit HTMLs, `model.json`, and raw
`generation.json`. Both complete A/B trees match, including the raw manifest
bytes. Every declared payload and intermediate also matches its manifest.
The original runner and external license texts match their input pins.

The PDF checks cover phone and Letter dimensions, fixed creation/modification
dates, expected Android control labels, and the unreviewed translation footer
on every Spanish page. PDF extraction can insert a space before a period; the
checker normalizes that extraction gap and also verifies the exact footer in
the corresponding HTML. Android-folder PDF copies match their root copies.

Both Android prompts contain the complete START section index, preserve the
warning and cards-win instructions, and state that full instructions are not
supplied. English uses 1,261 bytes and Spanish uses 1,306 bytes, within the
11,519-byte budget of the configured 16,384-token running context. Laptop
settings remain at 32,768 tokens; model metadata still reports a 262,144-token
native context. This verifies packaging and budgeting, without evaluating
answers or physical phone operation.

Only after complete equality was established were canonical copies created in
`build/generated/local_llm_sample` and `build/generated/local_llm_full`. Every
canonical file was rehashed against both builds. The ordinary
`ck verify-prepared` command then checked both refreshed catalog pins,
dependency hashes, placed files, and epoch inside a network-disabled pinned
container. The six pending size/hash/recipe markers are replaced with these
measurements; all existing review holds remain.

The older 71/54 outputs and
[historical repeat receipt](evidence/local-llm-repeat.json) remain untouched.
No SDK/tool archive enters these bundles, and no app, key, signature, or
full-drive image was produced by this repeat. Source correspondence, notices,
SDK/component terms, delegated Emoji/TTS behavior, device checks, content
review, and release approval remain open as recorded in the
[adoption handoff](android-local-llm-adoption.md).
