# Imported video and captions

Each clip declares all original audio and embedded subtitle streams. Optional
external subtitle inputs name catalog entries. The normalizer orders languages
from `languages.yaml`, writes one picture track with separate `mov_text` subtitle
tracks, and adds no text overlay. A translated subtitle is not a second audio
track. The source note must say which languages actually exist.

Caption packet times are checked before video encoding. Every declared stream
must contain timed cues, and every cue must fit the original audio/video span.
The pipeline fails rather than trimming a sentence, silently dropping captions,
or extending a short clip to accommodate an unrelated editing timeline. Embedded
caption times use their shared source media's origin.

An external caption may declare `time_offset_seconds` when a source-specific
alignment has been established. The default is zero. The configured shift is
recorded in `audit.json`; the input file remains byte-identical in the cache.
An embedded caption cannot shift its shared picture/audio input. An offset is
not inferred from the first cue or guessed to make a file pass the bounds check.
Fitting the bounds does not establish synchronization; watch the entire clip
with each caption track before clearing its catalog review gate.

## Confirmed publisher input needing alignment

USGS's [National Preparedness Month Spotlight on Earthquakes, part 5](https://www.usgs.gov/media/videos/part-five-drop-cover-and-hold)
links both its downloadable MP4 and English WebVTT. The page explicitly labels
the work public domain and credits Peter Pearsall, USGS. The original downloads
are pinned in `catalog/video.yaml` as build inputs only.

The downloaded video lasts 50.4504 seconds. Its linked WebVTT starts at
00:27:32.417 and ends at 00:28:18.930. Those timestamps do not fit that clip.
The preflight rejects the actual file without launching an encoder. No offset,
Spanish translation, corrected edition or physical playback result is claimed.
The candidate remains outside drive placement until its alignment is verified
and a complete normalized output is measured and pinned.

The currently selected CDC handwashing ASL conversion has original English
audio. It has no publisher-supplied Spanish audio or subtitle track; it cannot
satisfy the bilingual playback checklist by itself. The checklist remains open.
