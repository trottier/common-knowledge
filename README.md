# Common Knowledge

Common Knowledge is a proposed read-only emergency USB drive for every U.S.
household. Every drive carries the same core, with eight randomly distributed
variants adding reference material. The core is designed to open on a phone
without internet, an app store or advance setup.

**This repository is the recipe, not the cargo.** Git holds code, original text,
configuration and a pinned source catalog. Build tools will fetch and verify maps,
archives, apps, fonts, models and imported media. Those files do not belong in git.

## Current state

Work-order step 1 is implemented: repository structure, licenses, governance,
a pinned Python 3.12/uv container, and an empty `ck` CLI with help and version
flags. There are no emergency instructions, PDFs, catalog entries or drive images
yet. The package version identifies the development scaffold; v0.1.0 has not been
released or approved for use.

The complete specification and work order are in [AGENTS.md](AGENTS.md).
[CLAUDE.md](CLAUDE.md) carries the same instructions.
[docs/roadmap.md](docs/roadmap.md) tracks the remaining steps.

## Run the scaffold

Install Docker with a running Linux container engine. From this directory:

```sh
make check
make cli
make package
```

`make check` builds `Dockerfile.build`, then runs Ruff, formatting checks and
pytest with networking disabled. `make cli` shows CLI help. `make package` writes
the source archive and wheel to the ignored `dist/` directory.

The build platform is Linux x86-64. Docker on an ARM Mac needs x86-64 emulation.
Dependency installation requires internet access; the installed scaffold CLI does
not. See [docs/reproducibility.md](docs/reproducibility.md) for the exact pins,
sources and current limits.

For an editor's local Python environment, use Python 3.12 and `uv sync --locked`.
The container is the authoritative build and validation environment. Future
JavaScript tooling uses Bun where compatible with the specified rendering stack.

## Layout

| Path | Purpose |
| --- | --- |
| `config/` | Shared defaults, variants, languages and build profiles (step 2) |
| `catalog/` | Pinned external sources and license proofs (step 5) |
| `content/` | Original Markdown and citations |
| `templates/`, `assets/icons/` | Document templates and original SVG pictograms |
| `pipelines/` | Atlas, directory, maps, reference, AI and media generation |
| `src/ck/` | Python CLI and build package |
| `tests/` | Automated checks |
| `docs/` | Project and build documentation |
| `.github/workflows/` | CI and publishing workflows in later steps |
| `site/` | Generated verification site; ignored by git |

## Contribute and license

Read [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
and [SECURITY.md](SECURITY.md) before contributing. Keep pull requests small and
use Conventional Commits.

Code, configuration, build tooling and repository documentation use Apache-2.0
([LICENSE](LICENSE)). Original drive text in `content/` and original pictograms
in `assets/icons/` use CC0-1.0 ([LICENSE-CONTENT](LICENSE-CONTENT)). Imported
material retains its own license and attribution; see [THIRD_PARTY.md](THIRD_PARTY.md).
