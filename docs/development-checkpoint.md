# Eight-variant development repeat

At source commit `b4af173f69fffb1e5dadf3fd8940d6aafb683687` and development epoch
`1793404800`, all eight development variants were built twice. Both independent
core builds produced 38 PDFs covering all 15 editions. For every variant, raw
image, compressed image and file-manifest SHA-256 values matched. The image
builder checked each manifest against the files read back from its FAT image.
The retained compressed files and manifest sidecars were then rechecked.
Both complete core file sets were independently rehashed, and their generation
manifests match byte for byte. This checkpoint includes the confirmed Pages URL
and revised Android map import guides.

The full measured record is [dev-image-repeat.json](evidence/dev-image-repeat.json).
It includes the source commit, build-container identity, core-manifest hash and
all eight image records. Raw images were removed after verification; compressed
images, hashes, file manifests and PDFs remain in `build/dev-repeat/` in the
checkpoint worktree. Generated images and imported files are not committed.

The command ran in the network-disabled Linux build container. `CACHE_DIR`
identifies the existing shared SHA-256 cache, and the working directory is the
frozen source checkout:

```sh
rtk proxy docker run --rm --network=none --platform linux/amd64 \
  --cpus=1 --memory=1g --volume "$PWD:/source" \
  --volume "$CACHE_DIR:/cache:ro" --workdir /source \
  --env PYTHONPATH=src --env CK_FONT_CACHE=/cache \
  --entrypoint /workspace/.venv/bin/ck common-knowledge-build:step23-b \
  build-profile --profile dev --variants 1 2 3 4 5 6 7 8 \
  --output build/dev-repeat --cache /cache --epoch 1793404800 \
  --commit b4af173f69fffb1e5dadf3fd8940d6aafb683687 --reproduce
```

Each development image is 256 MiB and contains the project's draft core only.
This is not a sample/full build, production-capacity measurement, release
approval or device-test result. Third-party cargo and its license/source gates,
corrected national outputs, sample/full image repeats, named content reviews,
physical checks and the confirmed release configuration remain outstanding.

The [earlier checkpoint](evidence/dev-image-repeat-622bddb.json) is retained as
historical evidence for its own source commit. Its hashes do not describe this
updated build.
