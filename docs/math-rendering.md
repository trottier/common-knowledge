# Reference equation rendering

The installed PDF renderer does not lay out source MathML fractions and scripts
natively. Leaving that markup in a reference article can change the visible
relationship between its numbers. The shared article converter now renders
source MathML through the catalog-pinned MathJax package before producing PDFs.
Original article text, source revision links and numeric literals are retained.

The renderer runs with `bun run pipelines/math/render.mjs <verified-package>` in
the existing network-disabled build container. The original MathJax 3.2.2 npm
tarball is fetched by reference, checked against publisher SHA-512 integrity and
pinned by SHA-256. The MathML/SVG modules load directly from that unchanged
package, without dependency resolution or an install script. Bun and MathJax
versions enter each generation manifest. This uses Bun for the new JavaScript
tool; the atlas renderer keeps its existing Node ABI contract.

Generated equations contain vector paths and local shapes. Scripts, external
resources, event attributes, rendering errors and nonempty fallback text are
rejected. Empty MathJax table alignment markers are allowed. Source equation
alternate text is retained as an accessibility label where provided. The
converter removes a paired Wikimedia fallback image only after that equation
renders successfully; other source figures remain explicitly unavailable.

Each audit records the parsed source MathML hash, generated SVG hash and count
of replaced math fallback images. Source article byte hashes identify the
unchanged publisher input. Original package license text and attribution are
included with each output pack, using unique names in the shared phrasebook
folder. Neither the renderer package nor its executable source is shipped on
the drive.

Preflight covered 36 equations across the 29 selected book articles and 29
equations across five emergency-reference articles: sterilization, altitude
sickness, ectopic pregnancy, hypoxia and pulse oximetry. Full PDF regeneration,
independent repeats, visual comparison and named clinical review remain required.
Vector output supports zoom; physical-device legibility is not established by
these automated checks. Earlier PDF generation pins are not reused for this
recipe.

The 15 phrasebooks and four selected reference packs have now completed matching
independent development builds with the equation renderer. Every recorded
payload and intermediate hash was checked in both builds and the canonical
copy: 19 generated items, containing 67 placed files per copy. The complete
158-article medical repeat is still running. These measurements do not replace
the named reviews or final release regeneration.

Implementation references: [MathJax direct module usage](https://docs.mathjax.org/en/v3.2/server/direct.html),
[MathML Core](https://www.w3.org/TR/mathml-core/), and the
[publisher package metadata](https://registry.npmjs.org/mathjax-full/3.2.2).
