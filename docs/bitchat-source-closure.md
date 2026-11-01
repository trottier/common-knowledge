# bitchat Rust source checkpoint

The original bitchat 2.2.0 application source identifies Arti commit
`ba421ece1acb47e5c554c2bfa043cc9156451bab` and a Cargo lockfile with 509
packages. The official Arti tag resolves to that commit. Its unchanged upstream
source archive supplies 43 local packages; the application source supplies the
JNI wrapper. All 465 registry source archives are pinned in
`catalog/bitchat_rust_sources.yaml` and linked through
`bitchat_android_source.inputs` for the release source collector.

The registry archives total 89,552,010 bytes. Every archive matches both the
publisher's lockfile checksum and the registry's version metadata. Registry sizes
match downloaded archive lengths, and license fields match package manifests. Catalog license
expressions are retained verbatim, including legacy syntax; they require review
before the existing release checks can accept them. Archives retain their original
bytes and notices, and no dependency payload is committed to Git.

All four Arti native libraries in the APK match the corresponding binaries and
checksum manifest in the original application source archive. This identifies
the recorded source inputs; it does not claim that Common Knowledge has rebuilt
the Android application. The whole upstream Arti source archive also includes
optional LGPL `equix` and `hashx` packages, which are absent from this wrapper's
lockfile. Their original license files remain in the source archive.

The [evidence record](evidence/bitchat-rust-sources.json) binds these checks to the
application, application source, lockfile, upstream archive, and registry source
catalog IDs. After building `Dockerfile.build`, repeat the Cargo source audit
with networking disabled:

```sh
rtk proxy docker run --rm --network=none --platform linux/amd64 \
  --volume "$PWD:/source" --workdir /source --env PYTHONPATH=src \
  --entrypoint /workspace/.venv/bin/python common-knowledge-build:dev \
  tools/audit_cargo_sources.py \
  --source-id bitchat_android_source \
  --lock-path tools/arti-build/Cargo.lock \
  --cache cache --output build/bitchat-cargo-audit.json
```

The audit checks the cache hashes, every registry package's identity and license
metadata, and every local package's exact version. It fails when a source is
missing, ambiguous, or inconsistent with the lockfile. It never grants a human
approval or marks the entire application's source closure complete.

The release build still needs the Java and Android dependency sources, complete
per-file license and notice review, independent source-pin review, and physical
offline installation and peer tests. The application lockfile includes Google
Play Services and ML Kit dependencies, and the APK contains additional native
libraries. This Rust checkpoint makes no redistribution or source-completeness
claim for those components. The APK itself and its review status are unchanged.
