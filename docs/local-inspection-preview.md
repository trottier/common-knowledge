# Local inspection tree

`tools/assemble_inspection_preview.py` combines a frozen, verified fifteen-edition
core with explicitly pinned map and supplementary-reference receipts. It creates
a fresh local folder and an external `.provenance.json`; existing outputs are
never replaced. This is development inspection, not normal sample assembly,
release approval, a disk image, or physical-phone acceptance.

Run it in the pinned build environment with `PYTHONPATH` pointing to the frozen
core source's `src/` directory. Supply `--root`, `--core`, `--maps`,
`--map-sha256` (the exact `prototype.json` byte hash), `--supplements`,
`--supplements-receipt`, `--supplements-sha256`, `--output`, `--epoch`,
`--core-source`, and `--map-source`. Keep source and component mounts read-only;
only the new output parent needs write access. No network or conversions occur.

The tool preserves component profiles, historical recipes, epochs, completeness
flags, source notices, review holds, and every copied file's hash. Known rights
remain required even for draft inspection. It checks current selected catalog
pins and Variant 1 placement, rejects unsafe paths and symlinks, retains all
supplement notices, and checks the configured PDF byte cap. Existing core copying
provides local laptop HTML with its documented font-reference cleanup.

`BACKUP` contains copies of START and the entire present phone pack. The manifest
covers every other tree file; its own hash is recorded outside the tree. No
copy-ready PDF index is invented when no generator is available. README lists
actual entry points and missing cargo; technical provenance stays in VERIFY and
the external receipt. The normal assembler and release gates are unchanged.
