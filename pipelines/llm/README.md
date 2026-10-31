# Local LLM bundle

`ck local-llm --profile sample --cache cache --output build/local-llm/sample --epoch EPOCH`
checks a pinned base GGUF and builds the launchers, local page, English and Spanish
START prompts, warning, license files and phone/print instructions. Use `--profile full`
for the full-profile model. Run inside `Dockerfile.build` with the verified font cache.
The model is a separate catalog item; it is not copied into this generated bundle.

Settings are in `settings.yaml`; source and license pins are in `catalog/llm.yaml` and
`catalog/apk.yaml`. Selection evidence and open reviews are in
[`docs/local-llm-selection.md`](../../docs/local-llm-selection.md).

The prompt byte budget conservatively reserves space within the configured context.
This checks packaging size, not whether an untuned model follows an instruction.
The user must read START and follow the cards. No tuning or evaluation is performed.
