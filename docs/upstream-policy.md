# Upstream waiting period

The publisher's waiting period is not yet set. Keep
`config/build.yaml: upstream_min_age_days` as a VERIFY marker until maintainers
choose it. Do not substitute an assumed duration or reset historical release
dates to the date a file was downloaded.

Before pinning a new upstream version, record `release_date` (an ISO date) and
`release_date_source_url` from its publisher, wait the configured period, and
inspect the publisher's security advisories. Record the actual check in
`security_advisories`, with `checked_on`, `status`, `source_urls`, and any open
`advisory_urls`. The check must follow the waiting period. Open advisories and
unreviewed or missing evidence block release. The command does not perform a
network search or grant a security review merely because a hash is pinned.

`ck validate --release` checks these records using the current UTC date. It
rejects missing dates and evidence, future dates, a release younger than the
configured period, and open or unreviewed advisories. Generated outputs use
their cataloged input releases; they do not need a fictitious upstream date.
Old catalog entries remain usable for explicitly labeled development/cache
inspection; that compatibility does not authorize a new upstream pin or make
the entries ready for release. Existing entries still need documented dates
and checks. Runtime libraries, container bases, and CI actions also require
maintainer review under the policy; catalog checks alone do not cover pins
outside the catalog.

Manufacturing remains separate from development publication. It requires two
independent maintainers' hardware-key signatures on the actual `SHA256SUMS`
and matching tagged full-image rebuilds published by at least two outside
groups. No signing key or simulated approval is supplied by the agent. The
printed card must be generated after all eight real manifests exist; the
on-drive card omits their hashes to avoid a circular dependency. These
physical-card and manufacturing evidence steps remain pending.
