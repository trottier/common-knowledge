# Local LLM START context

The expanded Spanish START text no longer fits the launcher's conservative
UTF-8 byte budget at the configured context size. Bundle generation now follows
the specification's conditional START inclusion rule. It includes the complete
START text in the system prompt when it fits. Otherwise the prompt receives
only exact section titles, with an explicit instruction that protocol text is
absent and must not be reconstructed from memory. It never takes a partial
medical protocol to make the text fit.

Both complete rendered START texts are always retained as `ui/start-en.txt` and
`ui/start-es.txt`. The browser links to the chosen edition and states whether
the local LLM receives full text or titles only. The generated settings record
that choice and the measured text/prompt sizes. A title index that cannot fit
also fails explicitly.

Context and per-message reserves come from `pipelines/llm/settings.yaml`. Before
inference, the browser counts UTF-8 bytes across the system prompt and complete
conversation, adds the configured message, output and context reserves, and
rejects an oversized request without clearing the question or adding a phantom
turn. This is a conservative estimate, not model-tokenizer measurement. The
runner still disables context shifting; server context errors require a new
conversation rather than silently discarding the safety prompt.

At development epoch 1793404800, independent sample and full bundle builds
matched complete generation records. Both payload copies and model audit hashes
were verified. The sample bundle is 44,076,690 bytes, with generation SHA-256
`25f7453a4dd06ec38d1a60a06091f55ed9eed0d46cda11bd13123ef36510c26c`.
The full bundle is 44,053,192 bytes, with generation SHA-256
`7d884919272b976ee5fd78eb4702a2715da89f27a49422c6d6874462be3d48ef`.
The common recipe is
`local-llm-v1-4a2707af6e3265b282f9408ffbef47c80a293cd15d095aecd6e62927289fbeec`.
The sample supplies full English text and a Spanish section index; the full
profile supplies section indexes for both editions. Full reference text is
retained in all four cases. The measured pins retain their review gates.

This changes transport and context handling only. It makes no model-quality,
clinical-validity or physical-device claim. All source, license and human-review
gates remain in place. Final release-epoch generation and device checks remain
required before release.
