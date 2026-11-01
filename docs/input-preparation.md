# Input preparation

`make sample` and `make full` build both pinned container stages, fetch the
selected catalog dependency closure, regenerate its derived inputs, verify each
measured result against the catalog, and only then run image assembly. Existing
source bytes can remain in the hash-keyed download cache. Generated inputs must
start in a fresh directory; they are not reused as evidence of a clean source
build. The sample workflow keeps only raw downloads in its shared cache.

`tools/prepare_profile.py` is a standard-library host dispatcher. Python, geodata,
PDF, video, Java and filesystem work runs inside the build container. Native
atlas rendering and PMTiles extraction run inside the atlas container. The
driver resolves both image tags to immutable local image IDs before starting.
Every container sees the same `/source`, `/work`, `/cache` and `/generated`
paths; source is read-only. Only explicit fetch containers receive networking.
A host Python interpreter dispatches Docker; it does not generate shipped files.

The graph is derived from the ordinary capacity planner's union across the eight
variants, including its prebuilt-map fallback and local-LLM placement decisions.
Pass `--variants 1` to `ck prepare-plan`, `ck check-profile`, or
`tools/prepare_profile.py` to prepare only Variant 1's complete dependency graph.
An omitted selector preserves the union of all eight variants. Invalid or
duplicate variants fail, and an explicit selection preserves every selected
item's existing review, license, and capacity gates. Full-profile release checks
remain global. This selector does not authorize reuse, clear review holds, or
change the image-building command's behavior.
Dependencies precede consumers. An unknown generator, cycle or missing dependency
fails instead of dropping an item. Core PDFs are rendered before the final
preparation plan so actual core bytes enter the placement decision. An assumed
capacity may inspect a plan but cannot execute a build.

Sample state and medical-PDF worker settings live in `pipelines/build.yaml`.
The directory worker limit remains in its existing settings file. National
Android parent selection still comes from the shared national map policy.
Each generated result must match its catalog size, manifest hash, input pins,
pipeline version and epoch. The atlas-point seed may be incomplete only as its
explicitly unplaced seed item; assembled outputs remain strict.

Source ZIMs placed only in the build-input catalog can contain audited repairable
embed/link defects. `ck fetch-build-inputs` checks their exact download bytes and
full structural/content audit, saving the regeneration-input report in
`cache/audits/`. The regeneration pipeline must then pass strict output checks.
A placed raw ZIM receives ordinary strict verification. Neither path bypasses
license/legal holds or claims that a malformed archive is a valid placed output.

Review gates run before downloading or generating content. Full preparation also
requires a clean checkout at the matching version tag and the confirmed release
epoch. `preparation.json` is written only after every selected pipeline succeeds;
it records selected items, epoch, source commit, dirty status and container IDs.
It is a preparation receipt, not proof of matching images or physical usability.
Image reproduction remains the responsibility of `ck build-profile`.

Use a new `build/sample-inputs` or `build/full-inputs` work folder for each clean
run. Preserve publisher snapshots, review evidence and download caches before
cleaning development work. A missing or changed original response must fail;
restore the matching published [source bundle](source-bundles.md) when an old
publisher URL no longer yields the captured bytes. Stable preservation of every
large original remains a release requirement.

The current catalog graph has been checked with an explicitly assumed nominal
32 GB capacity for inspection only: no production capacity has been measured.
Automated tests cover graph ordering, missing adapters, legal holds, raw versus
placed ZIM audits, read-only mounts, network boundaries and native-render failure
propagation. The actual sample/full profiles are not declared successful while
catalog pins, rights, content review and physical tests remain unresolved.


The first real dispatcher smoke run completed in the dedicated Linux amd64
environment: all 38 development core PDFs rendered, no third-party input was
selected by the dev profile, and the preparation receipt recorded the resolved
container IDs and dirty development checkout. This checks real dispatch and
shared paths. It does not establish sample/full execution or image reproduction.
