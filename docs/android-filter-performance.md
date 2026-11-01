# Streaming Android map filter

The filter keeps untagged reference geometry without calling Python for every
node. `osmium cat` first removes contributor UID, user and changeset metadata
in a streaming pass. Versions, timestamps, coordinates and member references
stay intact. Only objects with tags enter the Python policy filter; native
fallback handling copies untagged reference objects directly to the writer,
in file order. This performance change preserves the prior filter semantics. The later
[point-label policy](android-point-labels.md) narrows settlement geometry and
removes orphaned reference objects; it requires new measured output pins.

The primary tool references describe
[metadata cleaning](https://docs.osmcode.org/osmium/latest/osmium-cat.html)
and [Pyosmium's empty-tag filter](https://docs.osmcode.org/pyosmium/latest/reference/Filters/).
The native fallback is important: bypassing Python must never bypass metadata
cleaning or lose road connections and turn restrictions.

A checked Rhode Island run with the pinned turn-restriction supplement took
13.2 seconds on this Mac's dedicated Linux environment. Its 9,872,628-byte PBF
matches the earlier checked filter output byte for byte:
`336bd4f7e096a8c8ab250e47242d1d7437dbd08cb83a6edab22597e827618676`.
The audit still counts 18,077 tagged nodes, 134,060 tagged ways, 1,381 tagged
relations and 101 excluded-tag removals. This is one observed runtime, not a
cross-machine speed claim.

The first full Oceania source check found 20 missing way references across
two island polygons. The U.S. check also found incomplete place polygons and
11 missing road members in border turn restrictions. These checks failed as
required. The subsequent [point-label policy](android-point-labels.md) and pinned
road supplements address those distinct causes without weakening reference
checks. The earlier Rhode Island hash above describes the performance-only
recipe, not the later filter policy.
