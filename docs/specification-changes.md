# Specification revision, 2026-10-30

The authoritative specification was supplied as `~/Downloads/AGENTS.md` and copied
to `AGENTS.md` and `CLAUDE.md`. The previously agreed manifest clarification is
retained: it covers every other image file; its own hash is published outside.

The kit uses one USB-C connector, with the whistle and compass in its body, attached
to the card. USB-A-only devices use a borrowed adapter. There is no dual-ended drive.

The config, catalog, planner, content and drive tree now use topics and in-depth
knowledge collections. Unresolved video-group placeholders now identify each
topic's video library; exact clips still need selection. The depth tree is
`6_VIDEOS_AND_IN_DEPTH/topics/` and
`6_VIDEOS_AND_IN_DEPTH/in_depth/`. Local model files use `9_LOCAL_LLM/` and the
term “local LLM”. Block Day has been removed from config and both full editions.

The card front includes the convener rule and blanks for rally point, out-of-area
contact and household medications. The back has the OK/HELP placard and four
original vector pictures of connecting and opening the drive. The card makes no
“first hour” promise; the START first-hour section remains. The tag sheet remains.

iFixit is removed from the active catalog. Red Cross, Stop the Bleed, Hesperian,
Khan Academy and iFixit need a written free emergency-use license before selection;
see [permission-requests.md](permission-requests.md).

The video pipeline must produce one MP4 with one picture track, no burned-in text,
and tagged narration/subtitle tracks in edition order. Imported source audio stays
first; select English-source clips to preserve the English-first default. Spanish
tracks follow English when present. MP3 companions are removed from the design.
Full narration for all fifteen editions belongs to v0.2. VLC for Android is a
candidate in `2_VIDEOS/android/`; its exact release, signer and corresponding
source archive remain unconfirmed.

Gemma 4 E2B is the first local LLM candidate. Google's
[model card](https://huggingface.co/google/gemma-4-E2B) lists Apache-2.0, a 128K context,
2.3B effective parameters and 5.1B including embeddings. The four-billion parameter
criterion needs clarification before selecting this candidate. An exact untuned
4-bit GGUF at most 2.5 GB and its checksum have not been confirmed. No evaluation
or fine-tuning claim is made.

The phone checklist now includes USB-A adapter use, English-default video playback
and audio/subtitle language switching. All physical-device checks remain pending.
