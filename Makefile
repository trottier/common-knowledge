BUILD_IMAGE := common-knowledge-build:dev
BUILD_PLATFORM := linux/amd64
DOCKER_RUN = docker run --rm --network=none --platform $(BUILD_PLATFORM) $(BUILD_IMAGE)

.PHONY: help build-container check lint test cli package

help:
	@printf '%s\n' \
	  'build-container  Build the pinned Python/uv environment (network required)' \
	  'check            Run lint, format checks and tests in the container' \
	  'lint             Run Ruff and check formatting in the container' \
	  'test             Run pytest in the container' \
	  'cli              Show ck help in the container' \
	  'package          Build Python source and wheel distributions into dist/'

build-container:
	docker build --platform $(BUILD_PLATFORM) -f Dockerfile.build -t $(BUILD_IMAGE) .

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
