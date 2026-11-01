# Initial topic video libraries

This development intake adds four short clips. Each is a minimal starting point
for a library, not comprehensive coverage of its topic. None has human approval
for emergency use. The catalog retains source, component-rights, safety,
caption, computed-pin, and physical-player review markers.

| Topic | Selected original | Scope |
| --- | --- | --- |
| Water and sanitation | [SFGovTV handwashing](https://commons.wikimedia.org/wiki/File:20200303_-_SFGovTV_-_SFDPH_WASH_HANDS_ENGLISH.webm) | A demonstrated handwashing sequence, plus sanitizer advice. Human review must check current guidance and the suitability of regional branding. |
| Food and cooking | [Navy summer grilling safety](https://www.dvidshub.net/video/1015054/summer-grilling-safety-2026) | Outdoor placement, lighting, and cleaning of a grill. Leak response and the unavailable-help branch need human review. |
| Convening and liaison | [FEMA Be Prepared](https://www.dvidshub.net/video/858801/fema-psa-prepared) | Household contacts, evacuation planning, alerts, and conversations with family, friends, and neighbors. This optional advice is not a prerequisite to opening the drive. |
| Transport and evacuation | [FEMA evacuation routes](https://www.dvidshub.net/video/858804/learn-your-evacuation-route-fema-psa) | Considering routes, pets, a destination, and official directions. Human review must cover accessibility and unavailable-help conditions. |

## Rights and original inputs

The SFGovTV file has an explicit Commons CC BY 3.0 declaration and a recorded
publisher-license check. Its downloaded original matches the Commons SHA-1
`6b8a8ea6a29d11075aa8af06ef59060188a9b9d6`. The project also computes and pins
SHA-256. [CC BY 3.0 sections 3 and 4](https://creativecommons.org/licenses/by/3.0/legalcode)
permit redistribution and adaptation with notice, attribution, and related
conditions. Recognition of this exact license does not accept NC, ND, unknown
terms, or unconfirmed third-party components.

Each selected DVIDS page identifies the federal producing agency, names its
creator, and declares that item public domain. The official embedded player
links the exact downloaded MP4 on `d34w7g4gy10iej.cloudfront.net`; no YouTube
download, playlist extraction, or player execution is involved. The
[DVIDS API copyright statement](https://api.dvidshub.net/docs/copyright)
describes federal production and the exception for other indicated rights.
The fuller [public-use notice](https://www.dvidshub.net/about/copyright)
preserves third-party, privacy, publicity, mark, and nonendorsement conditions.
These exceptions still need independent per-item review.

The intake guard recognizes that exact CDN and its repeated `DOD_` filename
structure only with a specific DVIDS video-page proof and the exact `US-PD`
declaration. A generic copyright page, another CDN, a lookalike domain, or an
unknown composite license does not qualify. This structural guard cannot prove
that an arbitrary CDN file belongs to an arbitrary item page. The recorded
publisher embed link, original hash, and independent human pin review establish
that correspondence for each catalog entry.

Original audio and picture remain intact in the input cache. Normalization adds
no burned text, narration, or MP3. Existing publisher titles and burned captions
remain part of the original picture. The three DVIDS clips also retain their
downloaded English WebVTT as switchable subtitle tracks, without correcting the
publisher's transcription mistakes. For example, the grilling captions contain
an awkward sentence about eaves and a leak-response statement needing review.
The SFGovTV source supplies one English audio stream and no embedded subtitles;
no captions were invented. Full input metadata is in the
[intake evidence](evidence/video-topic-intake.json).

## Language pairing and rejected candidates

No new clip claims a Spanish track. Two apparent language pairs failed the
picture/action requirement:

- SFGovTV English and [Spanish handwashing](https://commons.wikimedia.org/wiki/File:20200303_-_SFGovTV_-_SFDPH_WASH_HANDS_SPANISH.webm)
  last 58.354 and 59.423 seconds. At 15 seconds, the English picture is a close-up
  while the Spanish picture is a wider sink view. Matching subject matter does
  not establish interchangeable audio timing. The Spanish WebM also labels its
  audio `eng`, despite its Spanish speech, so its container tag cannot establish
  language. It was not relabeled, force-aligned, or placed.
- FEMA's English and [Spanish evacuation PSAs](https://www.dvidshub.net/video/858799/learn-your-evacuation-route-spanish-psa)
  use different presenters and different publisher text. Their audio was not
  combined onto either picture.

Other researched originals remain outside the active full-profile cargo:

- [Pasta sauce](https://commons.wikimedia.org/wiki/File:How_to_make_pasta_sauce.ogv)
  is described as CC BY-SA 4.0 on Commons, but both original Ogg streams embed
  `http://creativecommons.org/licenses/by-nc-sa/3.0/` and an Internet Archive
  origin. This concrete conflict blocks selection; the apparently freer page
  label did not override the original notice.
- [CFA radiant heat](https://commons.wikimedia.org/wiki/File:Description_of_radiant_heat_of_bushfires_by_the_Country_Fire_Authority,_Victoria,_Australia.webm)
  has a CC BY 3.0 label and an explicit warning that its external license has
  not been checked. It remains a research lead, with content and component
  rights unresolved.
- [Macaroni and cheese](https://commons.wikimedia.org/wiki/File:How_To_Make_Macaroni_and_Cheese.webm)
  is declared own work under CC BY-SA 3.0, but research did not establish useful
  English narration or suitability as emergency instruction. No track-language
  or suitability claim was invented.
- The [2026 Army CO PSA](https://www.dvidshub.net/video/997402/carbon-monoxide-safety-psa)
  captions say that over 100,000 people are hospitalized each year. This statistic
  conflicts with the [current CDC page](https://www.cdc.gov/carbon-monoxide/about/index.html),
  which distinguishes emergency-department visits from hospitalizations. It was
  not imported as established safety guidance.
- The [2021 Air Force CO clip](https://www.dvidshub.net/video/819983/carbon-monoxide-safety)
  includes historical statistics, model-dependent alarm signals, and caption
  transcription problems. The [2024 battery reminder](https://www.dvidshub.net/video/939862/smoke-and-carbon-monoxide-detector-change-batteries-reminder)
  is tied to a specific past clock-change date. Neither was selected.
- Two CDC food MP4s downloaded successfully, but the available general reuse
  policy and Commons public-domain labels did not establish a publisher
  per-video component-rights statement. They remain research leads. The old
  linked CDC CO and tornado MP4 endpoints returned 404.

Research transcription used the already-cached English-only Whisper model as
an aid for English source inspection. It is not a human review, a shipped
caption source, or evidence for Spanish accuracy. Its attempt on Spanish audio
explicitly fell back to English and is excluded from language conclusions.

## Remaining library gaps

The universal CDC handwashing clip starts the critical-video set. The existing
sketchbook clip starts the psychosocial library, and the existing rope clip is
optional transport depth with explicit load-safety holds. These real entries
replace redundant umbrella placeholders with measured, repeated generation pins.

Medical depth, care for dependents, power and utilities, structures/fire/search,
communications, welfare/reunification, and legal/recovery still need selected
topic clips. Their unresolved catalog entries remain. An aligned bilingual
publisher picture/audio source, subtitle review, source currency, safety
approval, and real phone language switching also remain open. The USGS clip
with an unresolved Envato component license is still held and excluded from
the eligible repeat set.
