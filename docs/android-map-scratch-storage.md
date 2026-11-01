# Map scratch storage audit

Read-only observations on November 1, 2026, confirm that the frozen split
producer writes its SQLite scratch databases through the host's shared
filesystem. A future controller can change the storage backing while retaining
the same paths, producer, inputs, image, and epoch. Its speed and byte equivalence
remain unmeasured. The current controllers and jobs were left unchanged.

The [observation receipt](evidence/android-map-scratch-observation.json) records
mounts, SQLite file signatures, active file sizes, six runtime samples, and the
completed Iowa command timings. `/artifacts` is a writable `virtiofs` bind from
the worker's host build directory. `build_split_map` puts its temporary directory
under the output's parent, including the converter's `work/` directory.

Florida's fifth regional input was 30,769,825 bytes. Its observed
`nodes.tmp.odb` was 766,726,144 bytes, and its main `.obf.tmp` database was
241,700,864 bytes. Both had SQLite format-3 headers. Georgia and Indiana also
had SQLite scratch files on their host-mounted output paths. These are live
snapshots, rather than peak-space measurements.

During a 5.016-second Florida sample, its cgroup used 4.269 CPU seconds and was
throttled in 27 of 50 quota periods. Java made 14,035 read calls and 4,341 write
calls, covering 57,487,360 read characters and 17,776,737 written characters.
The observed I/O-pressure counter increased by three microseconds. Each thread
snapshot showed one runnable Java thread and fourteen threads waiting on futexes.
The CPU quota was active; these measurements do not isolate shared-filesystem
latency as the dominant cost. Character counters include cached I/O, and block
I/O counters describe a different accounting layer.
[Kernel counter definitions](https://docs.kernel.org/filesystems/proc.html),
[cgroup CPU accounting](https://docs.kernel.org/admin-guide/cgroup-v2.html).

The completed two-part Iowa commands took 1,217.805 and 1,286.548 seconds; its
source extraction took 257.835 seconds. These whole-command times include
verification, filtering, partitioning, conversion, and inspection. They are not
isolated SQLite benchmarks. The observed container root filesystem had
60,014,538,752 available bytes; a future trial must check its selected volume's
backing filesystem and measure actual peak usage.

Use the following sequence for a separately scheduled experiment:

1. Start from the exact frozen producer commit, image `c9792c3f…`, measured Iowa
   extract, one CPU, 6 GiB, disabled networking, and epoch `1793404800`. Preserve
   `/source`, `/cache`, and `/prepared` as read-only mounts. Select a new run ID
   and an independently owned volume and container.
2. Mount a fresh Docker named volume at `/artifacts`, replacing the host output
   bind. Keep the original `--output /artifacts/IA/map-a` path. All temporary
   SQLite, region, and converter files then share that volume. This requires no
   producer-code or recipe-fingerprint change. Docker-managed volumes persist
   outside a container's lifecycle; see [volume semantics](https://docs.docker.com/engine/storage/volumes/).
3. Retain the exited producer container and its volume. Validate the complete
   metadata, input pins, epoch, payloads, and intermediates through a separate
   verifier with the volume mounted read-only. Preserve failure diagnostics.
4. Copy the complete result into a fresh host staging directory with
   `docker cp CONTAINER:/artifacts/IA/map-a/. STAGING`. Rehash every bound file
   after transfer, then compare complete metadata and all hashes with the
   already-matched Iowa host pair. Docker supports copying from stopped
   containers; see [copy semantics](https://docs.docker.com/reference/cli/docker/container/cp/).
5. Repeat with another fresh volume. Record conversion time, validation time,
   export time, end-to-end time, peak scratch size, and resource counters.
   Accept the host result atomically only after both local runs match the host
   baseline. Retain each original until its export is verified.

Adoption for future work depends on those measured results and an explicit
worker handoff. The experiment has separate outputs and must not claim a state
already owned by the running queue. Keep memory and CPU limits unchanged during
this storage comparison. Space planning must include retained regional inputs,
completed parts, and scratch files. Clean up only the experiment's exact owned
containers and volumes after verified export and retained receipts.
