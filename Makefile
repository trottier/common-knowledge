BUILD_IMAGE := common-knowledge-build:dev
BUILD_PLATFORM := linux/amd64
ATLAS_IMAGE := common-knowledge-atlas:dev
LLM_UI_IMAGE := oven/bun:1.3.11-slim@sha256:478281fdd196871c7e51ba6a820b7803a8ae97042ec86cdbc2e1c6b6626442d9
DOCKER_RUN = docker run --rm --network=none --platform $(BUILD_PLATFORM) $(BUILD_IMAGE)
SOURCE_DATE_EPOCH ?= $(shell git show -s --format=%ct HEAD)
SOURCE_COMMIT := $(shell git rev-parse HEAD)
CACHE_DIR ?= $(CURDIR)/cache
GENERATED_DIR ?= $(CURDIR)/build/generated
REPOSITORY ?= trottier/common-knowledge

.PHONY: help build-container atlas-container atlas-check llm-ui-check check lint test cli package dev sample full release-assets site clean

help:
	@printf '%s\n' \
	  'build-container  Build the pinned Python/uv environment (network required)' \
	  'check            Run lint, format checks and tests in the container' \
	  'atlas-check      Build and test the pinned native map renderer offline' \
	  'llm-ui-check     Test the local LLM browser interface with pinned Bun' \
	  'lint             Run Ruff and check formatting in the container' \
	  'test             Run pytest in the container' \
	  'cli              Show ck help in the container' \
	  'dev              Build core PDFs and a verified development image of variant 1' \
	  'sample           Build variants 1 and 3 twice from prepared, verified inputs' \
	  'full             Build all eight full variants twice from prepared inputs' \
	  'release-assets   Gate and package PDFs, eight dev images and GPL sources' \
	  'site             Build the verification site from published manifests' \
	  'clean            Remove generated build/ output before a clean rebuild' \
	  'package          Build Python source and wheel distributions into dist/'

build-container:
	docker build --platform $(BUILD_PLATFORM) -f Dockerfile.build -t $(BUILD_IMAGE) .

atlas-container:
	docker build --platform $(BUILD_PLATFORM) --target atlas -f Dockerfile.build -t $(ATLAS_IMAGE) .

atlas-check: atlas-container
	docker run --rm --network=none --platform $(BUILD_PLATFORM) $(ATLAS_IMAGE) test

llm-ui-check:
	docker run --rm --network=none --volume "$(CURDIR):/source:ro" \
	  --workdir /source --entrypoint bun $(LLM_UI_IMAGE) test pipelines/llm/ui/app.test.js

check: build-container
	$(DOCKER_RUN) ruff check .
	$(DOCKER_RUN) ruff format --check .
	$(DOCKER_RUN) pytest -q

lint: build-container
	$(DOCKER_RUN) ruff check .
	$(DOCKER_RUN) ruff format --check .

test: build-container
	$(DOCKER_RUN) pytest -q

cli: build-container
	$(DOCKER_RUN) ck --help

package: build-container
	mkdir -p dist
	docker run --rm --network=none --platform $(BUILD_PLATFORM) \
	  --volume "$(CURDIR)/dist:/artifacts" --entrypoint uv $(BUILD_IMAGE) \
	  build --offline --out-dir /artifacts

dev: build-container
	mkdir -p build
	docker run --rm --network=none --platform $(BUILD_PLATFORM) \
	  --env SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) --volume "$(CURDIR)/build:/artifacts" \
	  $(BUILD_IMAGE) ck core --output /artifacts/core
	docker run --rm --network=none --platform $(BUILD_PLATFORM) \
	  --env SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) --volume "$(CURDIR)/build:/artifacts" \
	  $(BUILD_IMAGE) ck plan --profile dev --core /artifacts/core
	docker run --rm --network=none --platform $(BUILD_PLATFORM) \
	  --env SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) --volume "$(CURDIR)/build:/artifacts" \
	  $(BUILD_IMAGE) ck image --variant 1 --profile dev --core /artifacts/core --output /artifacts/images

clean:
	rm -rf -- build

# Inputs are prepared and pinned separately. No target silently drops an item.
sample: build-container
	mkdir -p build "$(CACHE_DIR)" "$(GENERATED_DIR)"
	docker run --rm --network=none --platform $(BUILD_PLATFORM) \
	  --env SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) \
	  --volume "$(CURDIR)/build:/artifacts" --volume "$(abspath $(CACHE_DIR)):/cache:ro" \
	  --volume "$(abspath $(GENERATED_DIR)):/generated:ro" \
	  $(BUILD_IMAGE) ck build-profile --profile sample --variants 1 3 --reproduce \
	  --commit $(SOURCE_COMMIT) --cache /cache --generated /generated --output /artifacts/sample

full: build-container
	test -z "$$(git status --porcelain)"
	test "$$(git describe --exact-match --tags HEAD)" = "v$$(docker run --rm --network=none --entrypoint /workspace/.venv/bin/python $(BUILD_IMAGE) -c 'from pathlib import Path; from ck.config import load_config; print(load_config(Path.cwd()).build.version)')"
	mkdir -p build "$(CACHE_DIR)" "$(GENERATED_DIR)"
	docker run --rm --network=none --platform $(BUILD_PLATFORM) \
	  --volume "$(CURDIR)/build:/artifacts" --volume "$(abspath $(CACHE_DIR)):/cache:ro" \
	  --volume "$(abspath $(GENERATED_DIR)):/generated:ro" \
	  $(BUILD_IMAGE) ck build-profile --profile full --reproduce --commit $(SOURCE_COMMIT) \
	  --cache /cache --generated /generated --output /artifacts/full

release-assets: build-container
	mkdir -p build "$(CACHE_DIR)"
	docker run --rm --network=none --platform $(BUILD_PLATFORM) $(BUILD_IMAGE) ck validate --release
	docker run --rm --platform $(BUILD_PLATFORM) --volume "$(abspath $(CACHE_DIR)):/cache" \
	  $(BUILD_IMAGE) ck release-sources --cache /cache
	docker run --rm --network=none --platform $(BUILD_PLATFORM) --volume "$(CURDIR)/build:/artifacts" \
	  $(BUILD_IMAGE) ck build-profile --profile dev --commit $(SOURCE_COMMIT) --output /artifacts/release-build
	docker run --rm --network=none --platform $(BUILD_PLATFORM) --volume "$(CURDIR)/build:/artifacts" \
	  --volume "$(abspath $(CACHE_DIR)):/cache:ro" $(BUILD_IMAGE) ck release-assets \
	  --core /artifacts/release-build/core --images /artifacts/release-build/images \
	  --cache /cache --commit $(SOURCE_COMMIT) --output /artifacts/release

site: build-container
	mkdir -p build verification/releases verification/full build/published
	docker run --rm --network=none --platform $(BUILD_PLATFORM) --volume "$(CURDIR)/build:/artifacts" \
	  --volume "$(CURDIR)/verification:/manifests:ro" $(BUILD_IMAGE) ck site --repository $(REPOSITORY) \
	  --manifest-dir /manifests/releases --manifest-dir /artifacts/published \
	  --full-manifest-dir /manifests/full --output /artifacts/site
