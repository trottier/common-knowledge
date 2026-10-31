# Published verification records

`releases/` holds reviewed copies of `release-manifest.json` from published GitHub
releases, named by version. Pages also downloads all published release manifests
and verifies them against the corresponding `SHA256SUMS`, so a later site rebuild
does not erase previously published hashes.

`full/` holds `build-manifest.json` from complete, independently repeated builds
of all eight full variants. Copy a manifest here only after checking the source
commit, input lock, build logs and actual image hashes. The site rejects partial
or non-reproduced full manifests. No example hashes are published as real images.

Full-image hosting remains a publisher decision. A hash record does not imply a
download host exists. Do not add private or expiring storage URLs to the catalog.
