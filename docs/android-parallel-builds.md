# Parallel Android map builds

The development run on November 1, 2026, assigns 35 remaining U.S.-parent
jurisdictions to three isolated producers. It preserves the earlier 19 matching
single-map pairs and leaves California and Colorado with their existing
controllers. This run is in progress. It does not establish a complete national
map set, application redistribution permission, or successful phone tests.

[The run plan](evidence/android-parallel-plan.json) records the jurisdiction
universe, disjoint assignments, source measurements, and actual container
resource inspections. The producer checkout is frozen at
`2b0ca26f1b32a00058f8b18791202ed23d793b71`. Code, configuration, and recipes remain
unchanged during the run. Each worker updates only its own measured catalog
pins, between that worker's containers.

A separate [preserved-pair checkpoint](evidence/android-preserved-pairs.json)
independently rehashes every recorded payload and intermediate in both copies
of all 19 earlier pairs, checks their complete metadata and manifest bytes for
equality, and checks their measured values against the existing catalog pins.
Their original producer files remain unchanged.

Colorado subsequently completed both unchanged single-map builds. The
[20-state checkpoint](evidence/android-single-map-pairs.json) rehashes every
payload and intermediate in both copies, verifies their identical generation
manifests, and verifies each prepared extract and all four prepared parent
sources. The 20 placed map payloads total 1,957,632,931 bytes. Their measured
catalog pins are adopted without changing any producer file or clearing a
review hold. California and the 35 parallel assignments remain separate.

| Worker worktree | Assigned jurisdictions |
| --- | --- |
| `73-android-worker` | FL, ID, KS, ME, MO, NC, NM, OH, PA, TN, VA, WV |
| `74-android-worker` | GA, IL, KY, MI, MS, ND, NV, OK, SC, TX, WA, WY |
| `75-android-worker` | IA, IN, LA, MN, MT, NE, NY, OR, SD, UT, WI |

Each worker first extracts one jurisdiction from the independently rehashed
prepared U.S. road source. It verifies the extraction's complete metadata,
payload, and intermediate audit before recording that input pin. Two separate
containers then run `ck android-map --split` with new output directories and
the same measured prepared extract. The unchanged publisher map-creator JAR
converts bounded regional inputs sequentially inside each container.

The controller accepts a state only when the complete A/B metadata and manifest
bytes match, and every bound payload and intermediate in both outputs has the
recorded size and SHA-256. Additional diagnostic files receive separate
checksums; their elapsed-time log text is not claimed to reproduce. A failed
state receives an explicit failure receipt, keeps its logs, and cannot receive
an accepted map pin. Other assigned states continue.

The exact Linux amd64 image is
`sha256:c9792c3f92d4c2bb4a532aab4b5528e7aa9998d1314fcf47a16d72353cd28d52`.
The dedicated `colima-common-knowledge-batch` environment provides four virtual
CPUs and 24 GiB of RAM. At most three map containers run together, each limited
to one CPU and 6 GiB, with networking disabled. Producer source, cache, and
prepared input mounts are read-only; the only writable host mount is the
worker's build directory. The fixed development epoch is `1793404800`; the release epoch
remains unset.

The ignored host controller, command receipts, logs, source checks, state claims,
and accepted-pair receipts live under `build/android-parallel/`. Full generated
payloads remain under each worker's ignored `build/<STATE>/` directory. Nothing
in those directories is imported binary cargo in git.

Acceptance of an individual pair is separate from national publication. A later
national collector must require every jurisdiction, bind every map part and
source database, and verify both complete source coverage and exact regional
subsets. The complete national collection, capacity checks, final image pairs,
human source review, OsmAnd permission gates, and physical import/GPS tests
remain outstanding.
