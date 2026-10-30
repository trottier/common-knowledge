# Common Knowledge

Common Knowledge is a proposed read-only emergency USB drive for every U.S.
household. Every drive carries the same core, with eight randomly distributed
variants adding reference material. The core is designed to open on a phone
without internet, an app store or advance setup.

**This repository is the recipe, not the cargo.** Git holds code, original text,
configuration and a pinned source catalog. Build tools will fetch and verify maps,
archives, apps, fonts, models and imported media. Those files do not belong in git.

## Current state

Work-order steps 1–6 are implemented: repository structure, licenses, governance,
a pinned Python 3.12/uv container, shared configuration, strict validation and
`ck coverage`, and offline phone/print PDF rendering with an RTL fixture.
All thirteen English sections, the card, tags and variant guide are drafts with
explicit source, safety-review and device-test markers. A development FAT32 image
has been built and verified. Full images remain blocked by unconfirmed inputs, measured
capacity and required human reviews.
The package version identifies development work; v0.1.0 has not been released
or approved for use. Unconfirmed release values remain explicit VERIFY markers.

The complete specification and work order are in [AGENTS.md](AGENTS.md).
[CLAUDE.md](CLAUDE.md) carries the same instructions.
[docs/roadmap.md](docs/roadmap.md) tracks the remaining steps.

## Run the scaffold

Install Docker with a running Linux container engine. From this directory:

```sh
make check
make cli
make package
make dev
```

`make check` builds `Dockerfile.build`, then runs Ruff, formatting checks and
pytest with networking disabled. `make cli` shows CLI help. `make package` writes
the source archive and wheel to the ignored `dist/` directory.

`make dev` writes the core PDFs and a verified, compressed development image to
`build/`. Run `make clean` before rebuilding those outputs. Development images
contain draft core documents; they do not contain third-party cargo or constitute
an approved emergency kit. See [docs/images.md](docs/images.md) for capacity,
manifest and reproducibility details.

After `make build-container`, inspect configuration and findability with:

```sh
docker run --rm --network=none --platform linux/amd64 common-knowledge-build:dev ck validate
docker run --rm --network=none --platform linux/amd64 common-knowledge-build:dev ck coverage --homes 5
```

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
