BUILD_IMAGE := common-knowledge-build:dev
BUILD_PLATFORM := linux/amd64
ATLAS_IMAGE := common-knowledge-atlas:dev
DOCKER_RUN = docker run --rm --network=none --platform $(BUILD_PLATFORM) $(BUILD_IMAGE)
SOURCE_DATE_EPOCH ?= $(shell git show -s --format=%ct HEAD)

.PHONY: help build-container atlas-container atlas-check check lint test cli package dev clean

help:
	@printf '%s\n' \
	  'build-container  Build the pinned Python/uv environment (network required)' \
	  'check            Run lint, format checks and tests in the container' \
	  'atlas-check      Build and test the pinned native map renderer offline' \
	  'lint             Run Ruff and check formatting in the container' \
	  'test             Run pytest in the container' \
	  'cli              Show ck help in the container' \
	  'dev              Build core PDFs and a verified development image of variant 1' \
	  'clean            Remove generated build/ output before a clean rebuild' \
	  'package          Build Python source and wheel distributions into dist/'

build-container:
	docker build --platform $(BUILD_PLATFORM) -f Dockerfile.build -t $(BUILD_IMAGE) .

atlas-container:
	docker build --platform $(BUILD_PLATFORM) --target atlas -f Dockerfile.build -t $(ATLAS_IMAGE) .

atlas-check: atlas-container
	docker run --rm --network=none --platform $(BUILD_PLATFORM) $(ATLAS_IMAGE) test

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
