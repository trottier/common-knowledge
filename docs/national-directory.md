# National public places directory

The final directory uses the checked national point snapshot and the completed
national atlas. Each jurisdiction gets one phone PDF, one Letter PDF and one
public source-data JSON file. Every entry retains its address when supplied,
coordinates, source date and exact atlas page/grid/point reference. Every page
says “May help; not confirmed open.” Source omissions remain disclosed.

Freeze the recipe before running these commands inside the build container.
Use the same epoch as the point snapshot and atlas:

```sh
ck directory-all --points build/national-points --atlas build/generated/national_atlas \
  --states DE RI --jobs 2 --output build/directory-smoke --epoch "$SOURCE_DATE_EPOCH"
ck directory-all --points build/national-points --atlas build/generated/national_atlas \
  --jobs 2 --output build/directory-national --epoch "$SOURCE_DATE_EPOCH"
```

Omit `--states` to build all Census jurisdictions represented by counties in
the point snapshot. The command checks the shared national inputs once, then
uses separate Linux PDF workers with a shared read-only snapshot. The bounded
parts keep a large state from requiring one enormous document layout in RAM.
Choose one to four workers explicitly; two is the default in
`pipelines/directory/settings.yaml`. Use the dedicated build environment's
resource limits described in [build-machine.md](build-machine.md).

The same wording helper serves the single-state and national pipelines.
County and category headings are emitted once per group. Place blocks keep
their related lines together. Each county is split into deterministic parts
with at most 250 places, as configured. A county with no matched public place
still has a directory section; missing FEMA profiles are labeled rather than
inferred. Parts retain the font policy and unsupported-glyph check described
in [geographic-fonts.md](geographic-fonts.md).

The parts merge into one PDF per format. A front contents list links to each
county's first page, and the part bookmarks remain available. Temporary
reserved `.invalid` link targets are replaced with PDF GoTo actions. The
merger fails on missing or duplicated county links, so these contents links
never need a server. Metadata dates and PDF IDs are deterministic. The source
parts are tagged by WeasyPrint; merged-directory accessibility needs review,
and the pipeline makes no PDF/UA certification claim.

Each state output is atomic and has a generation manifest plus a bound
`state.json` coverage audit. The audit records place IDs, county IDs, part
limits, part checksums, PDF page counts and county starting pages. A failed
batch may leave completed state outputs; those are checked individually and
do not constitute a complete national set. Retry missing states into a new
batch directory. Do not overwrite or silently skip an output.

Collect the explicit state folders after every build succeeds:

```sh
ck directory-collect --points build/national-points \
  --atlas build/generated/national_atlas \
  --outputs build/directory-national/*/ \
  --output build/generated/national_directory --epoch "$SOURCE_DATE_EPOCH"
```

Collection checks every jurisdiction, exact county and place coverage,
matching recipe/source pins/epoch, public data against the checked national
snapshot, complete payload hashes, valid county page references and absence
of temporary contents URLs. Missing states, duplicated places or changed
audits fail. The national item is universal; its measured byte count enters
the capacity planner. No places or jurisdictions are removed to fit capacity.

Pin the resulting `national_directory` only after collection. Repeat clean
builds before publishing release hashes. Source and license pin review,
accessibility review and physical phone checks remain separate release gates.

The first actual smoke build completed Delaware (609 places; 345 phone pages,
145 print pages) and Rhode Island (812 places; 454 phone pages, 195 print pages).
Their total payloads are 1,054,007 and 1,401,384 bytes respectively. The full
56-jurisdiction build is running; national size/hash pins remain unconfirmed.
