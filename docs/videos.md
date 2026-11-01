# Imported video and captions

The [initial topic intake](video-topic-intake.md) records four additional
development selections, exact publisher provenance, rejected candidates, and
the libraries that still need clips. All human review gates remain open.

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

Earlier research left the water, food, and power topics unfilled. The
[new intake](video-topic-intake.md) adds water and food clips; power still needs
a selection. These earlier attempts did not establish eligible downloadable
originals, so no speculative catalog entries were added:

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
read-only source tree and cache, epoch 1793404800, one CPU, and a one-GiB memory
limit. All seven eligible clips used the same frozen recipe. Every MP4, source
notice, audit, and complete generation manifest matched byte for byte. The
[repeat evidence](evidence/video-repeat.json) records the pinned container image,
input hashes, full generation metadata, track summaries, and subtitle timings.
Placed bytes include the MP4 and its source notice.

An earlier repeat set used the producer before a formatting-only change. It is
retained as [historical evidence](evidence/video-repeat-preformat.json), with
the preformat and subsequent formatted source hashes and an AST-equivalence
check. The current
measurements below were rebuilt twice from the final formatted source; earlier
results were not relabeled with the new recipe fingerprint.

The following cross-context attempt exposed different MP4 chunk tables in the
rope clip despite identical compressed packets and timestamps. Its
[failed-repeat evidence](evidence/video-repeat-mux-failure.json) remains explicit.
The final producer sets output format `bitexact` and `max_interleave_delta=0`,
so sparse subtitles do not trigger timeout-driven interleave flushes.
[FFmpeg documents these output options](https://ffmpeg.org/ffmpeg-formats.html#Format-Options);
the pinned 5.1.9 help and [bounded mux diagnostics](evidence/video-mux-diagnostic.json)
confirmed their availability.
The table below comes from fresh normalizations of that final producer, not
from remuxing or relabeling a prior artifact.

| Clip | Placed bytes | Canonical generation SHA-256 |
| --- | ---: | --- |
| sfgov_handwash | 4,400,945 | `69ec74095901e1643f004cee9f96e64337d0b2bcc676ca12e5e6fb7a857bbce9` |
| summer_grilling | 4,912,069 | `1656639eaae8bf8a29e9f86ce68d84d04699ee861ac744385ff9b4608a6db3d9` |
| be_prepared | 2,701,117 | `4e6a9cdf69f55fa80d64ae23a837bf262f54c273c8838b174f94844557d6bab1` |
| evacuation_route | 3,417,514 | `b7184349229d7cbc5cf92f96f13597229d9d41e93b42fe54082b840d3cf016b0` |
| rope_middle | 36,694,698 | `7ec8bb44974d2a79bc29de8348bb1b1fbba24ac15004cf18972ef079d0d4709c` |
| simple_sketchbook | 14,399,595 | `8faffed4af5e4991d1d4ad752cb66f314fb1c5c7492e29a5f0bc032e5fcfb42c` |
| handwashing_asl | 10,813,105 | `ee6a3834141810c6da1fca55d45dc1bbdfefa72bb83dcdf18d14b6a32910a2e5` |

The catalog hashes canonical generation JSON. The evidence also records the
literal generation-file hash. All seven clips use H.264 Main picture at 480×854
and 30 fps, with the original English audio content converted to mono AAC as
the first and default audio track. English subtitles remain separate: 49 cues
for the rope clip, 23 for grilling, 13 for preparedness, and 14 for evacuation.
The other clips have no subtitle track. No Spanish track was invented, and no
new text was burned into the picture.

The shared recipe changed, so all three previous eligible clips received new
generation pins alongside the four additions. The obsolete critical-video,
water, food, convening, transport, and psychosocial umbrella placeholders were
removed in favor of these real entries. Seven topic libraries still need clips;
the [intake notes](video-topic-intake.md) describe their exact scope and gaps.

These measurements establish bounded conversion reproducibility. Source rights,
content suitability, independent pin review, caption accuracy and synchronization,
and physical-player review remain unapproved. The USGS clip with an unresolved
Envato component license was not rerendered or represented as current eligible
output.
