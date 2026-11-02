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
covers every other tree file; its own hash is recorded outside the tree. README lists
actual entry points and missing cargo; technical provenance stays in VERIFY and
the external receipt. The normal assembler and release gates are unchanged.

Additional cached cargo, short guides, and medical framing proofs have separate
admission helpers. They authenticate the existing tree and each added component,
preserve historical recipes and review holds, and write fresh output folders.
The medical framing helper compares every clinical body against its authenticated
parent; it does not approve the medical instructions.

`tools/build_map_finder.py` indexes county PDFs actually present in the tree.
`tools/build_copy_index.py` lists the actual shareable files and sizes, grouped
by folder. Attach these PDFs with `tools/attach_copy_index.py` against the exact
source manifest. Regenerate the copying index after changing its indexed cargo;
do not reuse an old index as if it described a new tree.

Open a finished tree with the existing CLI:

```sh
rtk proxy ck --root . explore --drive /absolute/path/to/inspection-tree --port 8766
```

The local explorer is at `http://127.0.0.1:8766/`. Numbered entry PDFs appear
before folders, so “Find a map,” “What to copy,” and short medical guides stay
easy to find. Optional reference and map data explain which reader they require
and remain inert in the website. Keep the incomplete status and missing cargo
visible. Publish only the separately exported representative hosted examples.
