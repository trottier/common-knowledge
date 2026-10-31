# v0.1 work order

Each numbered item is one pull request. The detailed requirements and definition
of done remain in [AGENTS.md](../AGENTS.md).

1. **Implemented:** scaffold, licenses, governance, pinned build container
   and initial `ck` CLI. Public review: https://github.com/trottier/common-knowledge/pull/1
2. **Implemented locally:** shared configuration, Pydantic models, `ck coverage`
   and invariants. Production capacity remains unconfirmed and fails closed.
3. **Implemented and tested:** templates, phone and print
   rendering for one English section, pinned fetched fonts and RTL fixture.
4. **Implemented as drafts:** all thirteen English START sections with citations,
   card, tags and variant explanation. Unverified safety procedures, QR targets
   and named human reviews remain explicit blockers; this is not approved content.
5. **Implemented and tested:** catalog schema, verified fetcher, all candidate
   families as explicit unresolved entries, release gate and attribution generation.
6. **Implemented and tested:** capacity planner, atomic assembler,
   real FAT32 images, manifest readback, normalized filesystem timestamps and CI.
7. **Implemented:** Spanish full edition, thirteen quick-start stubs, localized
   README lines, machine-translation notices and cataloged fonts for every script.
   Source hashes require retranslation when English instructions or defaults change.
8. National directory pipeline, starting with one small state.
9. Road atlas pipeline, starting with one small state.
10. Android map pipeline and planner-selected build path.
11. ZIM placement and medical phone PDFs.
12. Experimental base model selection, runners, Android entry and system prompt.
13. Imported media, documents, phrasebooks and forms.
14. Sample, reproducibility, release and Pages workflows; build-machine docs.

After step 14, stop and write `docs/release-review.md` with every remaining
VERIFY marker, legal sign-off and required human content review. Do not describe
the project as ready until the full definition of done is met.
