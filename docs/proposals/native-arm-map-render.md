# Same-pinned native ARM map rendering comparison

The native Linux ARM image rendered the actual 02827 leaf in 4.42 s, compared
with 8.88 s for the pinned amd64 image running through emulation on the same
ARM VM. With the explicit source-geometry cache enabled, native rendering took
4.00 s. These are observed render-only ratios of about 2.01× and 2.22× for this
one partial-county leaf, not a statistical or national speedup claim.

The three runs used the same pure-Python wheel, detached c4f1249 source,
authenticated prepared scene and fonts, 1 CPU/2 GiB limits, no network, fixed
hash seed, locale, timezone, and source epoch. The actual installed import path
and code bytes were checked. Python distribution versions all match; actual
Python build strings, native libraries, image IDs, system packages, and resource
receipts are recorded in the [evidence](../evidence/native-arm-leaf-2026-11-01.json).

Both PDFs (2 + 15 pages), every SVG, all rendered HTML, and the complete
cache-disabled prototype metadata are byte-identical across architectures.
There are no floating metadata differences in this leaf. Native cache-on also
preserves all payload bytes and coverage; its metadata differs only by the
explicit flag and corresponding render recipe. It releases all 2,163 cache
entries on exit; setup took 0.00041 s. All 405 named source ways remain covered.

The previous complete-source and installed-wheel regressions remain necessary.
One passing leaf does not establish cross-architecture equivalence for every
county or pipeline. Preserve the canonical amd64 recipes and old artifacts,
and keep the native image an explicit development choice until broader frozen
comparisons pass. This experiment changes no release platform or default flag.
It measures CPU-native rendering and caching; no GPU or Rust path was added.
