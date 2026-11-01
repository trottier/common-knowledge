# Earthquake clip caption alignment

The original USGS English VTT retains an editor timeline: its first cue starts at
00:27:32.417. The linked video is 50.4504 seconds long. The unshifted captions
correctly fail the existing media-timeline preflight; neither source file was
changed or silently discarded.

A local speech/word-timing comparison supports a development shift of
**-1652.417 seconds**. That maps all 32 original cues to 0.000–46.513 seconds.
The source caption text contains 141 normalized words; the independently decoded
audio produced 141 words, of which 140 align in sequence. The largest matched
word-midpoint excursion outside its shifted cue is 0.527 seconds (the word
“and” in cue 14). This is evidence of alignment, not frame-accurate caption
certification. Independent listening and physical playback review remain gates.
The publisher caption wording and cue spacing are retained.

| Anchor word | Shifted publisher cue (seconds) | Recognized speech (seconds) |
| --- | --- | --- |
| Welcome | 0.000–1.101 | 0.000–0.840 |
| drop | 13.647–16.049 | 14.000–14.340 |
| elevators | 27.094–29.196 | 27.920–28.380 |
| Please | 43.877–44.978 | 44.440–44.660 |
| content | 44.978–46.513 | 45.920–46.180 |

The source and caption SHA-256 values are recorded in `catalog/video.yaml`.
The normalized clip uses the existing ffmpeg pipeline inside the pinned build
container, preserves original English audio, and adds the publisher captions as
a separate `mov_text` track. It has no Spanish audio or subtitle track. Human
source-currency, rights/pin and synchronization checks are still unconfirmed.

## Research method

This timing research is separate from the shipped local LLM and makes no claim
about its quality. Research used Python 3.12.12 on the Mac, faster-whisper 1.2.1,
CTranslate2 4.8.4 and the MIT-licensed
[Systran tiny.en conversion](https://huggingface.co/Systran/faster-whisper-tiny.en)
at revision `0d3d19a32d3338f10357c0889762bd8d64bbdeba`.
The [publisher documents word timestamps](https://github.com/SYSTRAN/faster-whisper#word-level-timestamps).
The model ran locally with CPU int8, two threads, beam size 5, English,
word timestamps enabled, no VAD and no conditioning on previous text.
No audio was sent to a transcription service.

The pinned container's ffmpeg decoded mono 16 kHz float32 PCM. Supplying that
array directly avoided a decoder API mismatch between the research environment's
PyAV 19.0.2 and faster-whisper. Publisher LFS SHA-256 values and sizes were checked
for model files that supplied them. Exact research requirements, model hashes,
word timings and alignment results remain in the ignored development artifact
folder; neither the research model nor its transcript is shipped or committed.
No ASR-generated wording replaces the publisher captions.

The offset is declared in `pipelines/video/clips.yaml`; preflight still rejects
any cue outside the original video. Both this clip and the existing CDC clip
must be remeasured and independently repeated after the recipe change.

## Repeated development normalization

This is historical engineering evidence. The current
[USGS source page](https://www.usgs.gov/media/videos/national-preparedness-month-spotlight-earthquakes-part-5)
identifies additional footage used with permission from Envato Elements. The
catalog blocks the clip pending exact redistribution rights and named legal
review; the measurements below do not establish those rights.

Two separate network-disabled Linux containers produced identical payloads and
complete generation metadata at epoch 1793404800:

| Clip | Placed bytes | Canonical generation SHA-256 |
| --- | ---: | --- |
| USGS Drop, Cover and Hold On | 4,023,964 | 1e80a8c6aad80f307d49f99ddcdb23ea7336b6b1d75b5505dd9657fb9e613049 |
| CDC ASL handwashing | 10,813,142 | dda2d060c97ef12bc92d4c95adda6090e36d5a0c8bfe2bfda67105bb4c069ba8 |

The USGS output has one H.264 picture track, one original-content English AAC
track and one English `mov_text` subtitle track. All 32 source cues passed the
explicit-shift timeline check. The existing CDC payload bytes remain unchanged;
its complete generation hash changes because the shared clip recipe changed.
These repeats establish conversion reproducibility, not human synchronization,
source-currency or physical-player approval.
