# Contributing

Read the entire [AGENTS.md](AGENTS.md) specification first. If a task conflicts
with it, ask the maintainer before changing code or content.

## Small changes

Follow the work order in section 16, with one pull request per step. Use
Conventional Commits, for example `chore: scaffold common knowledge build tools`.
Describe the problem, resulting behavior, checks run and any unresolved markers.

Run `make check` before submitting. All authoritative builds and checks use the
pinned `Dockerfile.build` environment. Keep Python dependencies in
`pyproject.toml` and commit the updated `uv.lock`. Use uv for Python and Bun for
new compatible JavaScript tooling; preserve the specified runtime contracts.

Update both `AGENTS.md` and `CLAUDE.md` together if the maintainer approves a
specification change. They must remain byte-identical.

## Sources and content

Do not invent facts, versions, URLs, sizes, licenses or hashes. Confirm them at
the primary source or add `[[VERIFY: describe what needs confirmation]]`.
Never mark content as human-reviewed on an agent's behalf. Medical, legal and
radio content needs a named human reviewer before release.

Keep shared defaults in configuration. Do not repeat their values in templates
or original text. No telemetry or network calls may be added to shipped content.

Imported cargo belongs in the catalog with a license proof and verified pins,
then in an ignored build cache. Never commit binaries larger than 5 MB. Do not
modify a publisher's release file; regenerate only through a pinned documented
pipeline. Include corresponding source archives when distributing GPL apps.

## Licensing contributions

By contributing code, configuration, tooling or repository documentation, you
license that contribution under Apache-2.0. By contributing original drive text
or original pictograms, you dedicate that contribution under CC0-1.0. Confirm
that you have authority to do so. Third-party work keeps its original license
and must meet the catalog and redistribution rules.
