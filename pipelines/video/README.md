# Imported video normalization

Run `ck video --clip handwashing_asl --cache cache --output build/video/handwashing --epoch EPOCH`
inside `Dockerfile.build`. Clip declarations contain catalog IDs, original audio
languages, subtitle IDs/stream numbers and a FAT-safe MP4 filename. Inputs are
checksum-verified; ffmpeg is limited to local-file and pipe protocols.

The picture is encoded once, scaled without cropping and letterboxed to 480 × 854
at 30 fps, H.264 Main/yuv420p and about 600 kbps. Original audio is retained as
mono AAC at 48 kbps. Original English audio comes first and is the only default.
Subtitle tracks use mov_text; no new text is burned into the picture. Any text
already present in an imported picture remains part of the source. No MP3 is made.
Full narration in fifteen languages starts with original videos in v0.2.

Every original audio and embedded subtitle stream must be declared. English,
Spanish and remaining edition order come from `config/languages.yaml`; ISO 639-2
tags are derived from the pinned Library of Congress table. Chinese script editions
share a language code but retain distinct track titles. External subtitle inputs
need their own catalog pins and license evidence. No translated subtitle is
invented when a publisher has supplied none.

ffprobe checks picture count, dimensions, codec/profile, pixel format, rate,
language tags, track order, mono audio and dispositions. The MP4 atom listing must
put moov before mdat. Duration is checked against actual source media packet times:
the selected WMV's declared container duration includes time beyond its last media
packet. The audit retains both values. Metadata dates and encoder threads are fixed.

The real CDC handwashing ASL clip has original English audio and no supplied subtitle
file. Two independent builds matched their MP4, source note, audit and manifest
(10,813,142 payload bytes). Source attribution, free availability and the required
non-endorsement notice travel with it. Pin review, source currency and physical
playback remain open. Synthetic tests additionally verify subtitle language order,
safe rejection of undeclared audio, identical encodes and an unchanged picture
when only subtitle words change.

CDC's linked generator MP4s returned 404 during source selection. The newer USGS
earthquake spotlight contains Envato footage; its general public-domain label does
not establish redistribution rights for that footage. Neither is placed. Collection
and topic placeholders remain visible until individual eligible sources replace them.
