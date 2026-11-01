# English and Spanish video-source research

The bilingual playback checklist remains open. The two new Commons topic clips
have English narration, and the rope clip has author English subtitles. They do
not supply a Spanish narration track. No translated narration was generated.
This separate research checkpoint records why several apparent language pairs
were not selected. [Download and probe evidence](evidence/video-language-research.json)
contains the exact researched files, computed hashes, sizes, and durations.
The source bytes remain in the ignored development research directory.

## NOAA tsunami animation

The [NWS tsunami resource page](https://www.weather.gov/safety/tsunami-outreach)
links official English and Spanish no-caption MP4s for *Tsunamis: Be Prepared
and Stay Safe!* The English file lasts 106.639875 seconds; the Spanish file lasts
108.041271 seconds. At 50 seconds, the English version has completed a drawing
that the Spanish version is still drawing. Matching dimensions and similar
lengths therefore do not establish a shared picture timeline. Both source audio
tags say `eng`, illustrating why the tag alone cannot establish spoken language.

No audio was remapped or retimed, and no single-picture combined file was made.
Complete narration/scene alignment, per-item redistribution rights, publisher
subtitle availability, and human suitability review remain unconfirmed. The
[NOAA Digital Coast description](https://coast.noaa.gov/digitalcoast/training/tsunamis-be-prepared.html)
confirms the title and language editions, but does not itself supply an explicit
per-item redistribution grant.

## NOAA Aquarius

The [NOAA repository record](https://repository.library.noaa.gov/view/noaa/13606)
labels *Ocean Today. Aquarius* public domain and links a Spanish-version MP4.
That file has one audio track tagged `eng`, no embedded subtitle track, and
visible Spanish open captions. Local research recognition of its opening
25 seconds recovered English corresponding to the publisher's English
transcript. A Spanish-version label does not establish Spanish narration.
No Spanish spoken track was confirmed.

There is also an unresolved policy distinction: the Ocean Today
[site information](https://oceantoday.noaa.gov/aboutsite.html) generally describes
public-domain content, while its [usage FAQ](https://oceantoday.noaa.gov/about.html)
asks users not to alter or transform videos. No interpretation or permission
exception was invented, and no normalization or catalog placement was made.

## CDC food-safety animation

The [Keep Foods Separate Commons description](https://commons.wikimedia.org/wiki/File:Keep_Foods_Separate.webm)
links the original CDC MP4. The initial urllib request returned HTTP 403, while
curl successfully downloaded the 160,293-byte file. Its full audio decoded to
1,099,776 float32 samples, all exactly zero. A silent track cannot demonstrate
switching narrated languages; its `eng` metadata is not evidence of speech.
No voice was synthesized or assigned to its silence.

## Research boundary

This inspection used native Mac ffmpeg/ffprobe 8.1.2 for metadata, representative
frames, and audio decoding. The Aquarius opening used the existing local
[captions research environment](caption-alignment.md), with word timestamps
disabled and no external transcription service. These checks do not certify
language quality, rights, full synchronization, source currency, or a physical
player. They are separate from the pinned Linux normalization repeat evidence.
No research-only source, frame, or transcript is placed on a drive or committed
as binary cargo.
