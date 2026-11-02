# Cached video local inspection

`tools/admit_cached_videos.py` admits exactly the existing CDC handwashing and
FEMA Be Prepared packets to a fresh local Variant 1 clone. It verifies the base
manifest and its external provenance, current catalog input pins and rights,
original generation manifests, source bytes, notices, historical audit files,
actual streams, and faststart. It retains both original generation recipes and
their epoch. The ISO table is build-only under the narrow existing code-use
grant; it is absent from the copied payloads and notices.

The clone removes only the obsolete copy index and its backup, adds the four
MP4/source-note files, and updates practical navigation and omissions. Other
base bytes remain unchanged. The existing copy-index builder and attachment
helper then index the actual new tree. The original base provenance stays
unchanged and is authenticated by path and SHA-256 rather than embedded again.

CDC is a universal sample/full item. FEMA is a full-profile convening supplement;
this local addition does not change normal sample selection. Both retain their
human pin, currency, safety, and physical-playback holds. Both have English
audio; FEMA also has publisher English subtitles. There is no Spanish audio
and no physical-phone or language-switching acceptance claim.

The focused tests exercise fresh-clone preservation, source notices, stale-index
removal, collision and ancestor rejection, backup consistency, and rights/legal
holds. Actual cached payload and track checks are recorded separately in
[evidence](../evidence/cached-videos-local-preview-2026-11-01.json).

The live v12 Explorer check at a generic 390 px width opened and played both
actual MP4s, displayed their exact sizes, opened each source note, and rendered
the fresh copy index. No script, console, HTTP, or external-network errors were
observed. Playback was muted for this desktop check; this does not establish
physical-phone, audible output, or Spanish language-switching acceptance.
