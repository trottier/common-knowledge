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

## USGS technical checkpoint with unresolved footage rights

USGS's [National Preparedness Month Spotlight on Earthquakes, part 5](https://www.usgs.gov/media/videos/part-five-drop-cover-and-hold)
links both its downloadable MP4 and English WebVTT and credits Peter Pearsall,
USGS. The [current publisher page](https://www.usgs.gov/media/videos/national-preparedness-month-spotlight-earthquakes-part-5)
also identifies additional footage used with permission from Envato Elements.
Its general public-domain label does not establish Common Knowledge's right to
redistribute that footage. Both video catalog entries retain explicit unresolved
component rights and require named legal review. No grant is claimed.

The downloaded video lasts 50.4504 seconds. Its linked WebVTT starts at
00:27:32.417 and ends at 00:28:18.930. Those timestamps do not fit that clip.
The original unshifted caption preflight rejected those timestamps. Later
[caption research and repeated normalization](caption-alignment.md) recorded an
explicit development offset and matching outputs. Those are historical technical
checkpoints, not permission to place the clip. Third-party footage rights,
independent caption review, source currency, and physical playback remain open.

The currently selected CDC handwashing ASL conversion has original English
audio. It has no publisher-supplied Spanish audio or subtitle track; it cannot
satisfy the bilingual playback checklist by itself. The checklist remains open.
Additional [language-source research](video-language-research.md) records
official language versions that were not combined.

## Commons topic libraries

Two additional development selections start the transport and psychosocial video
libraries. [Tying off onto the middle of a rope](https://commons.wikimedia.org/wiki/File:Tying_off_onto_the_middle_of_a_rope.webm)
by Slashme demonstrates rope handling; [How to make a simple sketch book](https://commons.wikimedia.org/wiki/File:How_to_make_a_simple_sketch_book.webm)
by Barry neeson provides a creative activity. Each description page identifies
own work and an explicit CC BY-SA 4.0 grant. Their exact original downloads,
Commons file timestamps, description revisions, publisher SHA-1 values, and
computed SHA-256 pins are recorded in [source evidence](evidence/video-source-pins.json).
The full downloads from the clean, query-free file URLs also match those pins.
No YouTube file was downloaded; the rope file's Commons history records an
uploader import, while the author grants the Commons-hosted work directly.

Both originals have English narration and no embedded subtitle streams. The
rope author also supplied [English TimedText](https://commons.wikimedia.org/wiki/TimedText:Tying_off_onto_the_middle_of_a_rope.webm.en.srt).
Revision 544523334 is fetched byte-identically as a separate SRT input; its text
and cue times are retained in a separate subtitle track. The sketchbook had no
TimedText pages in the recorded Commons namespace search. Neither selection
provides a Spanish track. Local speech recognition helped inspect the complete
narration; its text is not shipped or used as captions. It used the existing
local research environment described in [caption alignment](caption-alignment.md),
without word timestamps. Representative source frames were also inspected.
This does not replace listening or human review.

These are optional depth selections. Human review must establish whether the
rope demonstration is suitable for load securing; it is not approved for
climbing, rescue, or towing. The craft uses scissors, a thumbtack, and unfolded
paper-clip wire; age suitability and supervision need review. Independent
source pin, rights, synchronization, and physical-player checks remain open.
No new captions, narration, burned-in text, or MP3 files are generated.

## Other source research

The preferred water, food, and power topics remain unfilled. These attempts did
not establish eligible downloadable originals, so no speculative catalog entries
were added:

- CDC's [Keep Foods Separate Commons description](https://commons.wikimedia.org/wiki/File:Keep_Foods_Separate.webm)
  links a CDC-hosted MP4. An initial urllib request returned HTTP 403, but a
  later curl download succeeded. Its decoded audio samples are all zero, so
  it does not supply narration for language switching. The Commons copy is
  public domain, outside this pipeline's specified Commons CC0/BY/BY-SA subset.
- The [CPSC carbon monoxide video page](https://www.cpsc.gov/Newsroom/Video/Carbon-Monoxide-Safety-Tips-For-Your-Home)
  exposed a YouTube player and downloadable captions, but no publisher-hosted
  video file was found. No player extraction was attempted.
- The [CDC generator record](https://stacks.cdc.gov/view/cdc/151499) supplies an
  archived-page PDF, rather than the linked video bytes.
- The [NWS lightning multimedia page](https://www.weather.gov/safety/lightning-multimedia)
  offered YouTube links and older links; tested direct/exit links returned
  HTTP 502 or 404. No usable download was selected.

The existing USGS clip's explicit component-rights hold is described above.
Other clips in that series with the same unresolved footage notice were not
selected as replacements.

## Repeated development normalization

Two separate network-disabled Linux containers per clip used the same verified,
read-only input cache and epoch 1793404800. Each MP4, source notice, audit, and
complete generation manifest matched byte for byte. The
[repeat evidence](evidence/video-repeat.json) records the pinned container image,
input hashes, full generation metadata, track summaries, and subtitle timings.
Placed bytes include the MP4 and its source notice.

| Clip | Placed bytes | Canonical generation SHA-256 |
| --- | ---: | --- |
| rope_middle | 36,679,027 | 9e766ee2fbb4631a38512da6ad232f39369a619630be24f898810d521bca72e2 |
| simple_sketchbook | 14,399,632 | 2a6a311743c62d3d880f03c0bf6f56e31aad264489b7b99b92563ddc3f754885 |
| handwashing_asl | 10,813,142 | 1d9c9d612ae82fecceee8631c2fcb024d9ddf443b5648d33bf7f567319b16341 |

The catalog hashes canonical generation JSON, without its trailing newline.
The evidence also records the literal generation-file hash. All three clips use
H.264 Main picture at 480×854 and 30 fps, with original-content English mono AAC
as the default audio track. The rope clip retains 49 separate English subtitle
cues; the other two clips have no subtitle track. The shared recipe changed,
so the existing CDC clip also received a new generation pin.

These measurements establish bounded conversion reproducibility. Source rights,
content suitability, independent pin review, caption synchronization, and
physical-player review remain unapproved. The USGS rights-held historical clip
was not rerendered or represented as current eligible output.
