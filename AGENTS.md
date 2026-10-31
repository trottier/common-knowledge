# AGENTS.md — Common Knowledge, v0.1

Instructions for an AI coding agent (Claude Code, Codex, Cursor or similar) building the public GitHub repository for **Common Knowledge**: a read-only emergency USB drive mailed to every U.S. household. Read this whole file before writing anything. If this file and a request conflict, ask the human.

**Git holds only what the project writes.** Code, original text, configuration and a pinned catalog of external sources live in git. Maps, Wikipedia, reference archives, apps, fonts, the local LLM and imported videos are fetched by reference at image-build time, verified by checksum, and never committed.

---

## 1. What the project is

Every household gets the same kit: a read-only USB-C drive with a whistle and compass built into its body, attached to a printed card. The drive works **with zero preparation**: on the day of an emergency, someone plugs it into a phone, taps, and it works with no internet, no app store and no setup. Older laptops, TVs and car stereos with only USB-A ports need an adapter, which a neighbor can lend.

**Why the design works.** Four mechanisms depend on each other, and the code must not weaken any of them:

- **Trusted sender.** An official, sealed, verifiable mailing. Hashes, the verification site and reproducible builds (§12, §13) are what make the trust checkable.
- **Universal reach.** Every household gets the same plan; nothing is opt-in.
- **Common knowledge.** Because the mailing is public and universal, everyone knows everyone else has the same defaults. That is why every default must render identically in every edition (§14).
- **Complementary variants.** Each drive holds a different part of the library, so neighbors have a practical reason to find each other. The same scheme keeps the cost per drive down.

Design rules that every line of code and content must respect:

1. **Zero preparation.** Nothing may depend on anyone installing, downloading or filling in anything beforehand. Core content opens in a phone's built-in Files app. The only installs allowed are optional one-tap Android installs (APKs) and double-click laptop programs.
2. **Phone-first, laptop-capable.** PDF and MP4 are the only formats the core depends on. ZIM archives, map files, apps and the language model are extras.
3. **Nationally standardized.** One national design. No per-city, per-county or per-address customization. Stable public places for every state and territory may ship; event-specific facts (which shelters are open, where water is handed out) and sensitive infrastructure never ship.
4. **Universal defaults replace coordination.** Rally point, meeting times, radio channel, mesh channels and convener rules come from one config file and render identically everywhere.
5. **Eight variants, shuffled at random.** Every drive carries the same core. Each variant adds video libraries for three of twelve topics plus one in-depth knowledge collection. Each topic appears on exactly two variants; each collection on one.
6. **Smallest correct release first.** Ship v0.1 from existing sources, then improve the content image; the hardware stays fixed.

## 2. Scope of v0.1

v0.1 assembles **everything that can be built from existing sources** into eight full drive images, plus the project's own core content.

**In scope:**

- The core: START document, card, tag sheet and "How is my drive different?" page, in English (reviewed) and Spanish (machine-translated, marked unreviewed).
- **All 15 language editions stubbed** (§9.2).
- A **road atlas** of every county with a latitude/longitude grid, and a **national places directory**, built from public data (§9.3, §9.4).
- **Android offline maps** for every state, plus the map app (§9.5).
- **Wikipedia-family and reference archives** (ZIM), with a curated set of medical articles converted to phone PDFs for iPhones (§9.6).
- An **untuned base local LLM** with offline runners for laptops and Android, marked experimental (§9.7).
- **Imported public-domain and openly licensed videos and documents**, normalized to the drive's spec, with narration and subtitle tracks stored in one file per clip (§9.8).
- **Phrasebooks**, radio and incident-command forms, and exam question pools (§9.9).
- The **mesh chat apps** (bitchat, Briar).
- The **eight in-depth knowledge collections**, populated from the catalog.
- A **capacity planner** that places every item, then an assembler that builds eight reproducible images, plus CI, releases, a verification site and tests.

**Out of scope for v0.1:** shooting original videos, tuning or evaluating the local LLM, the block-board app, human-reviewed translations beyond Spanish, hardware procurement and mailing.

## 3. Hard rules

**Never:**

- Invent facts, numbers, doses, frequencies, URLs, versions, sizes, licenses or checksums. Look them up from the primary source, or write a `[[VERIFY: ...]]` marker (§10).
- Commit large binaries (anything over 5 MB: archives, APKs, models, map data, fonts, videos, images) to git. Reference them in the catalog and fetch at build time.
- Include anything whose license does not allow redistribution on a free government-distributed drive. Red Cross, Stop the Bleed, Hesperian, Khan Academy and iFixit (noncommercial license) materials are **out** until a free emergency-use license is granted in writing; the project will request one from each. In-depth knowledge collections use only public-domain or openly licensed material that needs no permission. YouTube rips are **out**; import only files hosted by the rights holder or by Wikimedia Commons.
- Add telemetry, analytics, network calls from shipped content, or `autorun.inf`. Executables may appear only in `6_VIDEOS_AND_IN_DEPTH/*/laptop/`, `7_LAPTOP/`, `8_MESH_CHAT/`, `9_LOCAL_LLM/` and any `android/` subfolder.
- Modify third-party files. Ship them byte-identical to the publisher's release, or regenerate them from source data with a pinned, documented pipeline.
- Ship per-locality data, event-specific shelter or distribution locations, or sensitive infrastructure (substations, water and wastewater plants, pipelines, dams, telecom sites).

**Always:**

- Keep one source of truth. Every default value is read from config, never retyped.
- Record every external item in `catalog/` with URL, version, size, SHA-256, license, attribution and placement.
- Make builds reproducible: pinned inputs, pinned build container, fixed timestamps (§12).
- Keep pull requests small, with tests. Use Conventional Commits.

## 4. Tech stack

| Purpose | Tool | License |
| --- | --- | --- |
| Language, env | Python 3.12 with `uv` (`pyproject.toml`, `uv.lock`) | PSF, MIT/Apache-2.0 |
| Build container | `Dockerfile.build`, base image pinned by digest | n/a |
| Markdown → HTML | `markdown-it-py` + `mdit-py-plugins` | MIT |
| Templating | `Jinja2` | BSD |
| HTML → PDF | `WeasyPrint` (bookmarks, internal links, font subsetting, right-to-left via Pango) | BSD |
| Config | `pydantic` v2, `PyYAML` | MIT |
| QR codes | `segno` | BSD |
| Geodata | `geopandas`, `shapely`, `pyproj`, `osmium` (Python) and `osmium-tool` | BSD, Boost |
| Atlas rendering | Node 20+ with `@maplibre/maplibre-gl-native`, `pmtiles` CLI | BSD-2, BSD-3 |
| Android map files | OsmAnd map creator (Java 17+) | GPL-3.0 (tool only) |
| ZIM reading | `python-libzim`; `zimcheck` from `kiwix-tools` | GPL-3.0 (tools only) |
| Local LLM | `llamafile` and/or `llama.cpp` builds | Apache-2.0 / MIT |
| Video | `ffmpeg` | LGPL/GPL (tool only) |
| APK checks | `apksigner` | Apache-2.0 |
| Disk images | `dosfstools`, `mtools`, `zstd` | GPL/BSD (tools only) |
| Lint, tests | `ruff`, `pytest` | MIT |

## 5. Repository layout

```
common-knowledge/
├── AGENTS.md  (copy to CLAUDE.md for Claude Code)
├── README.md, LICENSE (Apache-2.0, code), LICENSE-CONTENT (CC0-1.0, original content)
├── THIRD_PARTY.md            # generated from catalog/
├── CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md
├── Dockerfile.build, Makefile, pyproject.toml, uv.lock
├── config/
│   ├── defaults.yaml         # rally rule, times, radio, mesh
│   ├── variants.yaml         # topics, variants, collections
│   ├── languages.yaml        # 15 editions: code, name in own script, script, direction, font
│   └── build.yaml            # profiles, capacity, volume label, site URL, SOURCE_DATE_EPOCH
├── catalog/                  # pinned external items, one YAML file per family
│   ├── zim.yaml, apk.yaml, fonts.yaml, maps.yaml, geodata.yaml,
│   ├── llm.yaml, video.yaml, docs.yaml, phrasebooks.yaml
│   └── medpdf_topics.yaml    # curated article list for iPhone medical PDFs
├── content/
│   ├── <lang>/start/*.md     # en and es full; others quick-start stubs
│   ├── <lang>/card.md, <lang>/tags.md
│   └── sources.yaml          # citations for original text
├── templates/                # Jinja2 HTML + CSS (phone, print, card, tags, atlas, directory)
├── assets/icons/             # SVG pictograms (CC0)
├── pipelines/
│   ├── atlas/                # Node renderer + page composer
│   ├── directory/
│   ├── androidmaps/
│   ├── zim2pdf/
│   ├── llm/
│   └── video/
├── src/ck/                   # Python package, CLI `ck`
├── tests/
├── docs/                     # content style, reproducibility, phone tests, build machine, roadmap
├── site/                     # generated; published to GitHub Pages
└── .github/workflows/        # ci.yml, sample.yml, release.yml, pages.yml
```

## 6. Configuration

### `config/defaults.yaml`

Use exactly these values.

```yaml
rally_point:
  rule:
    - written_on_card
    - nearest_public_elementary_school_main_entrance
    - nearest_fire_station            # if no school within walking distance
    - nearest_place_of_worship        # if neither of the above
meetings:
  times_local: ["12:00", "18:00"]
  if_nobody_there: "Leave a dated note and return at the next time."
convener:
  rule: "The first adult at the rally point at noon opens the meeting with the one-page script."
  rotation: "Each meeting ends by choosing the next convener. No one serves two days running."
  role_fallback: "A role nobody picks falls to whoever holds a drive variant with that topic, until someone better steps up."
radio:
  service: FRS
  channel: 3
  frequency_mhz: 462.6125
  privacy_code: none
  listen_window: "First five minutes of every hour"
mesh:
  app: bitchat
  channels: { block: "#block", help: "#help" }
  formats: { help: "HELP · {address} · {need}", ok: "OK · {address}" }
  schedule: "Turn on at the top of each hour with the radio window; leave on if power allows."
```

### `config/variants.yaml`

```yaml
topics:
  medical:      { category: body,  title: "Medical" }
  care:         { category: body,  title: "Care for dependents" }
  water:        { category: body,  title: "Water and sanitation" }
  food:         { category: body,  title: "Food and cooking" }
  power:        { category: infra, title: "Power and utilities" }
  structures:   { category: infra, title: "Structures, fire and search" }
  comms:        { category: infra, title: "Comms and information" }
  transport:    { category: infra, title: "Transport and evacuation" }
  convening:    { category: civic, title: "Convening and liaison" }
  welfare:      { category: civic, title: "Welfare and reunification" }
  legal:        { category: civic, title: "Legal, money and recovery" }
  psychosocial: { category: civic, title: "Psychosocial, kids and morale" }
collections:   # in-depth knowledge, one per variant
  howto_1:    "How-to library, part 1"
  howto_2:    "How-to library, part 2"
  laptop_map: "Interactive map for laptops"
  med_lib:    "Medical library"
  repair:     "Repair and engineering"
  simplewiki: "Simple English Wikipedia and travel guides"
  school:     "School lessons for disrupted schooling"
  morale:     "Public-domain books, music and games"
variants:
  1: { topics: [medical, power, convening],     collection: howto_1 }
  2: { topics: [care, structures, welfare],     collection: howto_2 }
  3: { topics: [water, comms, legal],           collection: laptop_map }
  4: { topics: [food, transport, psychosocial], collection: med_lib }
  5: { topics: [medical, structures, legal],    collection: repair }
  6: { topics: [care, comms, psychosocial],     collection: simplewiki }
  7: { topics: [water, transport, convening],   collection: school }
  8: { topics: [food, power, welfare],          collection: morale }
```

Invariants (tested): each topic on exactly two variants; each variant has one body, one infrastructure and one civic topic; collections unique. `ck coverage` prints findability, where *k* is the number of variants carrying an item and *n* the number of nearby homes: P = 1 − (1 − k/8)^n.

### `config/languages.yaml`

Fifteen editions. Ranking must match U.S. Census data on residents with limited English proficiency; confirm before release.

```yaml
# status: full | machine | stub
- { code: en,      name: "English",          script: Latn, dir: ltr, font: noto_sans,      status: full }
- { code: es,      name: "Español",          script: Latn, dir: ltr, font: noto_sans,      status: machine }
- { code: zh-Hans, name: "简体中文",          script: Hans, dir: ltr, font: noto_sans_sc,   status: stub }
- { code: zh-Hant, name: "繁體中文",          script: Hant, dir: ltr, font: noto_sans_tc,   status: stub }
- { code: vi,      name: "Tiếng Việt",       script: Latn, dir: ltr, font: noto_sans,      status: stub }
- { code: tl,      name: "Tagalog",          script: Latn, dir: ltr, font: noto_sans,      status: stub }
- { code: ko,      name: "한국어",            script: Kore, dir: ltr, font: noto_sans_kr,   status: stub }
- { code: ar,      name: "العربية",          script: Arab, dir: rtl, font: noto_sans_arabic, status: stub }
- { code: ru,      name: "Русский",          script: Cyrl, dir: ltr, font: noto_sans,      status: stub }
- { code: ht,      name: "Kreyòl ayisyen",   script: Latn, dir: ltr, font: noto_sans,      status: stub }
- { code: pt,      name: "Português",        script: Latn, dir: ltr, font: noto_sans,      status: stub }
- { code: fr,      name: "Français",         script: Latn, dir: ltr, font: noto_sans,      status: stub }
- { code: fa,      name: "فارسی",            script: Arab, dir: rtl, font: noto_sans_arabic, status: stub }
- { code: pl,      name: "Polski",           script: Latn, dir: ltr, font: noto_sans,      status: stub }
- { code: hi,      name: "हिन्दी",            script: Deva, dir: ltr, font: noto_sans_devanagari, status: stub }
# [[VERIFY: confirm the list and order against current ACS limited-English-proficiency data]]
```

### `config/build.yaml`

```yaml
version: "0.1.0"
android_maps: auto              # auto | roads_places; one map strategy for all variants
volume_label: "EMERGENCY"
volume_id: "0C0FFEE0"
site_base_url: "[[VERIFY: GitHub Pages URL]]"
source_date_epoch: "[[VERIFY: set at release]]"
profiles:
  dev:    { third_party: none,   image_size_mib: 256 }                # CI on every push
  sample: { third_party: sample, image_size_mib: 4096 }               # one small state, small archives, tiny model
  full:   { third_party: all,    capacity_bytes: "[[VERIFY: measured usable bytes of the production 32 GB part]]",
            reserve_fraction: 0.03 }
```

## 7. The catalog (by-reference content)

Every external item is one entry:

```yaml
- id: wikem_en_nopic
  family: zim
  title: "WikEM, no pictures"
  url: "[[VERIFY: exact download.kiwix.org URL]]"
  version: "[[VERIFY]]"
  size_bytes: "[[VERIFY]]"
  sha256: "[[VERIFY]]"
  license: "CC BY-SA 4.0"
  attribution: "WikEM contributors, packaged by Kiwix"
  license_proof_url: "[[VERIFY]]"
  placement: universal            # universal | topics: [...] | collection: <id> | hub_only
  dest: "5_MEDICAL_REFERENCE/"
  profiles: [sample, full]
```

Rules:

- Take URLs, versions, sizes and checksums **only** from the publisher's official pages or checksum files. Where a publisher gives no checksum, download over HTTPS, verify (signer certificate for APKs, `zimcheck` for ZIMs), and pin the hash in a reviewed pull request.
- APK entries add `signer_cert_sha256` and `source_url`. The release attaches the exact corresponding source archive for every GPL app.
- `license_proof_url` points to the page that states the license. Items without one cannot be placed.
- Generated items (atlas, directory, Android map files, medical PDFs) record their **input** items and pipeline version instead of a download URL.

### Candidate items for v0.1

Every size and URL below must be confirmed. Sizes marked *Kiwix* come from Kiwix metadata measured in September 2026.

| Item | Family | Approx. size | License | Placement |
| --- | --- | --- | --- | --- |
| WikiMed, English, no pictures | zim | 862 MB (Kiwix) | CC BY-SA 4.0 | universal |
| WikEM, no pictures | zim | 347 MB (Kiwix) | CC BY-SA 4.0 | universal |
| Wikivoyage, English, no pictures | zim | 272 MB (Kiwix) | CC BY-SA 4.0 | collection: simplewiki |
| Simple English Wikipedia, no pictures | zim | 1.09 GB (Kiwix) | CC BY-SA 4.0 | collection: simplewiki |
| WikiMed, English, with pictures | zim | 2.22 GB (Kiwix) | CC BY-SA 4.0 | collection: med_lib |
| Medical Wikipedia in other editions' languages | zim | [[VERIFY]] | CC BY-SA 4.0 | collection: med_lib |
| Appropedia | zim | 582 MB (Kiwix) | CC BY-SA 4.0 | collection: repair |
| iFixit | zim | 3.57 GB (Kiwix) | CC BY-NC-SA 3.0 | collection: repair, **only after iFixit grants a free emergency-use license** |
| U.S. Army Publishing Directorate collection | zim | 8.23 GB (Kiwix) | U.S. federal works | split: medical manuals to med_lib, technical to repair, [[VERIFY: distribution statement A only]] |
| Project Gutenberg subject collections | zim | [[VERIFY]] | public domain in U.S. | collection: morale |
| Education collections (for example PhET simulations) | zim | [[VERIFY]] | [[VERIFY]] | collection: school |
| English Wikipedia (text-only 52.7 GB, intros-only 14.4 GB) | zim | Kiwix | CC BY-SA 4.0 | hub_only (too large for 32 GB) |
| Kiwix for Android; Kiwix desktop for Windows, Mac, Linux | apk, binaries | [[VERIFY]] | GPL-3.0 | universal (`android/`, `7_LAPTOP/`) |
| bitchat for Android; Briar | apk | [[VERIFY]] | GPL-3.0 | universal (`8_MESH_CHAT/`) |
| OsmAnd for Android | apk | [[VERIFY]] | GPL-3.0 | universal (`3_MAPS_AND_PLACES/android/`) |
| Noto fonts per script | fonts | [[VERIFY]] | OFL-1.1 | build input only (subset embedded in PDFs) |
| FEMA, Ready.gov, CDC, EPA, NWS guides, including official translations | docs | [[VERIFY]] | U.S. federal works | universal or by topic |
| FEMA incident-command (ICS) forms | docs | ~8 MB | U.S. federal works | topic: comms |
| Amateur radio exam question pools | docs | [[VERIFY]] | [[VERIFY: public domain]] | topic: comms |
| Federal agency-hosted how-to videos; Wikimedia Commons videos | video | [[VERIFY]] | federal or CC | topics (video libraries), or universal if critical |
| VLC for Android | apk | [[VERIFY]] | GPL-2.0 / LGPL [[VERIFY]] | universal (`2_VIDEOS/android/`), for choosing a video's language track |
| Gemma 4 E2B, 4-bit GGUF | llm | [[VERIFY]] | Apache-2.0 [[VERIFY: confirm on the model card]] | universal if it fits, else four variants (§8) |

## 8. Capacity planner and variant creation

`ck plan --profile full` reads the catalog and generated-item size estimates, then for each of the eight variants:

1. Adds universal items.
2. Adds the variant's three topics' items (video libraries).
3. Adds the variant's in-depth knowledge collection.
4. Compares the total to `capacity_bytes × (1 − reserve_fraction)`.

It prints a per-variant table and **fails** if any variant overflows, naming the largest items. Humans resolve overflows by moving items (universal → topics, or collection → hub_only) in the catalog, never by silently dropping content.

**Placement decision rules,** applied in this order:

1. The core (START, card, phone pack, both copies) is always universal.
2. The atlas and directory are always universal: everyone needs their own area, and mailing is random.
3. Android map files are universal. If prebuilt files overflow, switch to the roads-and-places build (§9.5) before moving anything else.
4. The local LLM is universal if it fits after rules 1–3; otherwise place it on four variants (k = 4, so it is within five homes 97% of the time).
5. Medical references are universal up to about 1.5 GB; the rest goes to `med_lib`.
6. Everything else fills the in-depth knowledge collections; what does not fit is `hub_only`.

`ck assemble --variant N` then builds each variant tree from the plan.

## 9. Pipelines

### 9.1 Core documents (START, card, tags)

- Markdown → HTML (Jinja2 templates) → PDF with WeasyPrint.
- **Phone PDF:** 90 mm × 160 mm pages, base type at least 12 pt, one column, tappable contents page, PDF bookmarks for every heading. **Print PDF:** US Letter.
- **Card:** half-letter, two-sided, attached to the drive. The front holds the rally rule, meeting times, convener rule, radio channel, mesh channels, write-in blanks (rally point, out-of-area contact, household medications) and three QR codes (videos page, state emergency agencies page, verification page). The back is a large OK/HELP placard and four pictures showing how to open the drive on an iPhone and on an Android phone.
- **Tags:** US Letter label sheet: GAS — ¼ TURN — WRENCH HERE; WATER MAIN; MAIN BREAKER; MEDS IN FRIDGE.
- The "How is my drive different?" page is generated from `variants.yaml` and the plan. It first lists what each variant holds (its three topics and its in-depth knowledge collection), then explains why drives differ: complementary content gives neighbors a reason to find each other and keeps the cost per drive down.
- PDF metadata dates come from `source_date_epoch` (`dcterms.created`/`dcterms.modified` meta tags). Use tagged or PDF/UA output if the installed WeasyPrint supports it.

**English START sections:**

1. How to use this drive: iPhone, Android, laptop; copying the phone pack; sharing by AirDrop or Quick Share.
2. The first hour.
3. Shutoffs (gas and when not to, water main, main breaker), plus generator carbon monoxide safety.
4. Water: hidden sources, and disinfection with EPA dosing quoted and cited.
5. Meeting your neighbors: rally rule, times, convener rule, the 15-minute meeting script.
6. Signals: OK/HELP placard, door check marks.
7. Communications: FRS channel 3, the bitchat channels, text rather than call, NOAA Weather Radio, satellite SOS, licensing notes.
8. Maps: finding yourself on the atlas with the iPhone Compass app (it shows degrees, minutes, seconds), the Android map app, the laptop map.
9. Medical basics, each with a "no help is coming" branch: bleeding control, hands-only CPR, recovery position, burns, heat illness, hypothermia, oral rehydration, medication continuity.
10. The local LLM: what it is, how to start it, and why the printed cards win when they disagree.
11. How is my drive different?
12. Warnings and use.
13. Sources.

### 9.2 Language editions

- **en:** full. **es:** full machine translation by the agent, with a footer on every page of each PDF: "Traducción automática sin revisar."
- **Every other edition (stub)** gets:
  - A folder named in its own script under `1_START/`.
  - A machine-translated **quick-start PDF** (phone and print): how to open the drive, the card defaults (rally rule, times, radio channel 3, the bitchat channels), the OK/HELP words, and where the English and Spanish full editions are. Each page carries an "unreviewed machine translation" footer in that language.
  - A localized line in the root `README.TXT`.
  - Official federal translations of preparedness guides in that language, imported from the catalog where they exist.
  - The Wikivoyage phrasebook for that language (§9.9).
- Right-to-left editions (ar, fa) render with `dir="rtl"`; tests check shaping by rendering a known string.
- Fonts are fetched from the catalog and subset into PDFs; none are committed.

### 9.3 National places directory

- **Sources** (confirm each endpoint, license and freshness):
  - Public schools: National Center for Education Statistics (EDGE school locations).
  - Public libraries: Institute of Museum and Library Services, Public Libraries Survey outlets.
  - Hospitals, urgent care, pharmacies, fire stations, police stations, post offices: OpenStreetMap via the Geofabrik U.S. extract filtered with `osmium tags-filter` (ODbL attribution).
  - Broadcast stations: FCC licensing data.
  - NOAA Weather Radio transmitters: National Weather Service station list.
  - County hazard profiles: FEMA National Risk Index county table.
  - State emergency agencies: an official federal list [[VERIFY: source]].
- **Output:** one phone PDF and one print PDF per state and territory, sorted by county, then category, then name. Each entry gives name, address, coordinates and atlas page plus grid square. Each source shows an "as of" date, and every page says "may help; not confirmed open."
- **Exclusion list in code:** substations, power plants, water and wastewater plants, pipelines, dams, telecom sites, government buildings beyond the categories above. A test fails if any excluded tag appears.

### 9.4 Road atlas

- **Inputs:**
  - A Protomaps basemap extract for the U.S., PMTiles (OpenStreetMap, ODbL) [[VERIFY: build URL and date]].
  - Census TIGER/Line cartographic county boundaries (public domain).
  - Census urban areas or places, for city insets.
  - Directory points.
- **Render:** a Node script uses `@maplibre/maplibre-gl-native` to draw each county to fit a page, plus insets for dense urban areas, as PNG at about 200 dpi equivalent.
- **Compose:** WeasyPrint adds a latitude/longitude grid labeled in both decimal degrees and degrees-minutes-seconds (the iPhone Compass shows DMS), grid letters and numbers, numbered directory points with a legend, a north arrow and scale bar, and ODbL attribution.
- **Output:** one PDF per state and territory, with a bookmark per county and an alphabetical index of places pointing to page and grid square.
- **Budget:** `atlas.max_total_bytes` with an image-quality setting; target about 3.5 GB for all states. Process states in parallel.

### 9.5 Android offline maps

- **Path A, prebuilt:** OsmAnd's official per-state map files, if OsmAnd's terms allow redistribution [[VERIFY: OsmAnd terms and per-state sizes from its index]].
- **Path B, roads and places:** Geofabrik state extracts filtered with `osmium` to roads, places and directory categories, then converted to OsmAnd's format with its map creator. Large states need splitting; see `docs/build-machine.md` for memory.
- Choose by size with the planner. Default to Path B if Path A overflows or its terms are unclear.
- Ship the OsmAnd APK. Write and phone-test a one-page how-to for importing a state's map file into OsmAnd from the drive [[VERIFY: exact import flow on current Android]].

### 9.6 Reference archives and iPhone medical PDFs

- ZIMs come from the catalog, are verified with `zimcheck`, and land in the placed folder with Kiwix readers alongside.
- `pipelines/zim2pdf`: reads the article list in `catalog/medpdf_topics.yaml` (start with about 150 high-yield topics from WikEM and WikiMed) using `python-libzim`, renders phone PDFs with CC BY-SA attribution and article dates, and places them in `5_MEDICAL_REFERENCE/pdf/`. These serve iPhones, which cannot install Kiwix offline.

### 9.7 Base local LLM (experimental, untuned)

- **Model selection criteria,** recorded in `catalog/llm.yaml` with the reasoning:
  - Open weights under Apache-2.0 or MIT; avoid custom licenses with use restrictions unless legal approves.
  - Strong multilingual coverage of the 15 editions.
  - Four billion parameters or fewer.
    For Gemma 4 E2B, count effective parameters (project publisher clarification); the separate 2.5 GB file limit still applies.
  - 4-bit GGUF of 2.5 GB or less.
  - Context window of 32K tokens or more.
  - Primary candidate: Gemma 4 E2B (Apache-2.0, built for on-device use; v0.4 plans an emergency fine-tune of it, ideally with Google). Alternates: current Qwen small models (Apache-2.0) and Phi mini models (MIT) [[VERIFY: latest versions, licenses, GGUF files and checksums]].
- **Laptop:** `llamafile` (or `llama.cpp` server) with the GGUF stored as a separate file, because Windows cannot run executables over 4 GB. Launchers: `Start Local LLM - Windows.bat`, `Start Local LLM - Mac.command`, `Start Local LLM - Linux.sh`. Each starts the local server on `127.0.0.1` and opens the browser.
- **Android:** an open-source app that loads a local GGUF file [[VERIFY: candidate app, license, current APK and checksum]], plus a how-to.
- **Grounding:** a system prompt in `pipelines/llm/system_prompt.md` that:
  - instructs short answers in the user's language,
  - requires pointing to the START section by title,
  - forbids inventing doses and other numbers,
  - says to follow the printed cards when in doubt.

  If the context window allows, it also includes the START text for that language.
- **Warning:** on the launcher page and in START: "Experimental local LLM. It can be wrong. If it disagrees with a card or video, follow the card."
- No tuning and no evaluation claims in v0.1.

### 9.8 Imported videos and documents

- Import only files hosted by a U.S. federal agency (public domain, confirmed per item) or Wikimedia Commons under CC0, CC BY or CC BY-SA. Record the proof URL per item.
- Normalize videos to the drive spec:
  - Vertical 480×854 where the source allows (otherwise letterbox to fit), 30 fps.
  - H.264 main profile, `yuv420p`, about 600 kbps, `-movflags +faststart`.
  - **One MP4 per clip; the picture is stored once.** Never burn text into the picture. Each language is an extra track in the same file: AAC mono narration (about 32–48 kbps) and a `mov_text` subtitle track, each tagged with its ISO 639 language code.
  - Track order: English first, Spanish second, then the other editions in `languages.yaml` order. Many default Android players, TVs and cars play only the first track, so English must be the default.
  - Imported videos keep their original audio as the first track and add subtitle tracks where translations exist; the full 15-language narration applies to the original videos in v0.2.
- Federal documents go in by topic, or universal if critical, with the original title and agency.

### 9.9 Phrasebooks, forms and question pools

- Wikivoyage phrasebooks for each edition's language (CC BY-SA 4.0), taken from the Wikivoyage ZIM or a pinned dump, rendered as phone PDFs.
- FEMA incident-command forms and radio exam question pools go into the comms topic, subject to confirmed licenses.

## 10. Content rules

- **Plain language.** Short sentences, one action per line, imperative mood, roughly 6th-grade reading level.
- **When not to.** Every action states when not to do it.
- **No help is coming.** Every medical and rescue protocol ends with a branch for when 911 does not answer.
- **Sources.** Every factual claim cites a source id from `content/sources.yaml`. Prefer primary U.S. federal sources. Federal text is public domain; images on federal sites may not be.
- **VERIFY markers.** Anything unconfirmed is written `[[VERIFY: ...]]`. Dev builds highlight markers in yellow. **Release builds fail if any remain,** in content, config or catalog.
- **Review status.** Content front matter carries `status: draft | reviewed | machine`, `reviewer:` and `reviewed_on:`. Medical, legal and radio sections need a named human reviewer for release. The agent never sets `reviewed`.

## 11. Drive layout

```
/README.TXT                 # every edition: "Open 1_START"
/VERIFY.TXT                 # version, variant, verification URL
/MANIFEST.SHA256            # SHA-256 of every other file on the image; own hash published outside
/1_START/<edition folder in its own script>/   # START or quick start, phone + print
/2_VIDEOS/                  # imported critical videos (universal), android/VLC.apk
/3_MAPS_AND_PLACES/
    atlas/<STATE>.pdf
    directory/<STATE>.pdf
    android/OsmAnd.apk, maps/<state>.obf, HOW_TO.pdf
/4_PHONE_PACK/              # phone PDFs + card, copy-ready
/5_MEDICAL_REFERENCE/       # ZIMs, pdf/, android/Kiwix.apk
/6_VIDEOS_AND_IN_DEPTH/
    topics/<topic>/         # this variant's three video libraries
    in_depth/<collection>/  # this variant's in-depth knowledge (laptop/ subfolder may hold executables)
/7_LAPTOP/                  # static HTML version, Kiwix desktop, map viewer launcher if placed here
/8_MESH_CHAT/               # bitchat, Briar, LICENSES/, SOURCE.TXT
/9_LOCAL_LLM/               # GGUF model, launchers, android/, WARNING.TXT
/BACKUP/                    # second copy of 1_START and 4_PHONE_PACK, FAT hidden attribute
```

File names must be FAT-safe: none of `\ / : * ? " < > |`, path length under 200 characters, numbered prefixes for sort order. Folder names may use any script, because FAT long names are UTF-16.

## 12. Assembler, images and reproducibility

- All builds run inside `Dockerfile.build`, pinned by base-image digest. Every tool version is recorded in the image's `VERIFY.TXT`.
- `ck image --variant N --profile P`:
  1. Sets every file's mtime to `SOURCE_DATE_EPOCH` with `TZ=UTC`.
  2. Runs `mkfs.fat -F 32 -n EMERGENCY -i 0C0FFEE0 -C <img> <KiB>`.
  3. Creates directories with `mmd` and copies files one by one in sorted order with `mcopy -m -Q` (`MTOOLS_SKIP_CHECK=1`).
  4. Runs `mattrib +h` on `/BACKUP`.
  5. Writes the manifest inside the image, and the manifest and image SHA-256 hashes outside it. The manifest covers every other image file, excluding itself (human clarification, 2026-10-30).
  6. Compresses with `zstd -19` and hashes the result.
  7. Checks the listing with `mdir -/`.
- **Reproducibility test:** two clean builds of variant 1 in the `sample` profile must produce identical image hashes. Normalize any nondeterminism (PDF IDs, archive timestamps) or document it in `docs/reproducibility.md` with an `xfail` test and an issue link.
- **Build machine for `full`** (`docs/build-machine.md`): Linux x86-64, at least 16 cores, at least 64 GB RAM (the OsmAnd map creator is memory-hungry on large states), at least 1 TB of free SSD, Java 17+, Node 20+. Cache downloads in `cache/` keyed by SHA-256.

## 13. CI, releases and distribution

- **`ci.yml`** (every push and pull request): ruff, pytest, `dev` profile build of all PDFs and variant 1, and an RTL rendering test. Upload artifacts.
- **`sample.yml`** (nightly and on demand, larger or self-hosted runner): `sample` profile, meaning one small state's atlas, directory and map file, WikEM, a tiny model, and both mesh APKs. Builds variants 1 and 3; runs the reproducibility test.
- **`release.yml`** (tag `v*`): fail on any VERIFY marker or unreviewed medical, legal or radio content. Publish to the GitHub Release: the PDFs, `dev`-profile images, the catalog lock, `SHA256SUMS` and GPL source archives. Each file must be under 2 GB.
- **Full images** are built from the tagged commit on the build machine with `make full`. They are too large for GitHub Releases. Publish their hashes on the Pages site; hosting (object storage, BitTorrent with web seeds, or both) is a human decision [[VERIFY: hosting choice]]. Because every input is pinned, anyone can rebuild and check the hashes.
- **`pages.yml`:** the verification site, with every image hash, how to check with `sha256sum`, `shasum -a 256` or `certutil -hashfile`, the catalog with licenses and attributions, and links to the PDFs.

## 14. Tests (minimum)

- Config and catalog schemas validate; every catalog item has license, proof URL, SHA-256, size and placement.
- Variant invariants hold; `ck plan --profile full` fits every variant within capacity.
- Every default appears verbatim in the card and START HTML for every edition.
- All 15 editions exist with folder, quick start and README line; RTL editions render correctly.
- Every citation id exists; release mode fails on any VERIFY marker.
- The directory contains no excluded categories; the atlas has one bookmark per county or county-equivalent [[VERIFY: current count]]; grid labels parse.
- Every video has one picture track, English as its first audio track, and audio and subtitle tracks tagged with valid language codes; no text is burned into new renders.
- File names are FAT-safe; no executables outside allowed folders; no `autorun.inf`.
- The manifest matches the image; the reproducibility test passes in `sample`.

## 15. Manual phone and laptop checklist (`docs/phone-test-checklist.md`)

Devices: an iPhone with USB-C, an iPhone with Lightning plus an adapter, a recent Pixel, a budget Samsung, a budget Motorola, and Windows, Mac and Linux laptops, including one with only USB-A ports (via a USB-C to USB-A adapter). Check that:

- The drive mounts; phone PDFs open; contents links and bookmarks work; text is readable without zooming.
- An atlas page opens on an iPhone, and the Compass coordinates locate the user on the grid.
- On Android, OsmAnd installs and a state map imports and shows a live GPS dot offline.
- Kiwix opens WikEM on Android and on laptops; the medical PDFs open on iPhone.
- bitchat connects two Android phones with all networking off; Briar shares itself offline.
- A video plays in English by default on every device; the iPhone player's menu switches to Spanish audio and subtitles; VLC does the same on Android.
- The local LLM launcher starts on each laptop OS and answers in English and Spanish; the Android app loads the model on a phone with at least 6 GB of RAM.
- The phone pack copies to a phone and sends to a second phone by AirDrop or Quick Share.

## 16. Work order (one pull request each)

1. Scaffold, licenses, governance files, `Dockerfile.build`, an empty `ck` CLI.
2. The four config files, pydantic models, `ck coverage` and invariant tests.
3. Templates and CSS; one English section rendered to phone and print PDFs; RTL test fixture.
4. English START sections with sources and VERIFY markers; card; tags; "How is my drive different?" page.
5. Catalog schema, `ck fetch` with verification, the candidate items as VERIFY entries, and `THIRD_PARTY.md` generation.
6. The planner and `ck assemble`, with dev-profile images, manifest and CI.
7. Language editions: Spanish full, 13 stubs, fonts via the catalog.
8. Directory pipeline (one small state first, then all).
9. Atlas pipeline (one small state first, then all).
10. Android maps pipeline (Path A or B per the planner).
11. ZIM placement and the zim2pdf medical PDFs.
12. Local LLM: selection notes (Gemma 4 E2B first), launchers, Android app entry, system prompt.
13. Imported videos (multi-track audio and subtitles, VLC entry) and documents, phrasebooks, forms.
14. Sample workflow, reproducibility test, release and Pages workflows, build-machine docs.

Then stop and write `docs/release-review.md`, listing every remaining VERIFY marker, every item needing legal sign-off or a granted license (iFixit, Khan Academy, Hesperian, Red Cross, Army publications, the model license) and every section needing human review.

## 17. Definition of done for v0.1.0

- `make full` on the build machine produces eight images that fit capacity, with published hashes; two clean builds match.
- CI and sample workflows are green; the dev-profile release is on GitHub with PDFs and GPL sources.
- All 15 editions exist; English is reviewed; Spanish and the stubs are marked as machine translations.
- No VERIFY markers remain; every catalog item has a confirmed license and proof URL; legal has signed off on flagged items.
- The phone and laptop checklist is complete on at least three phones and two laptop operating systems.

## 18. Roadmap after v0.1 (context only)

- **v0.2:** original vertical how-to videos (the 50 critical clips), narrated and subtitled in all 15 languages, replacing imports where better.
- **v0.3:** reviewed translations for all editions.
- **v0.4:** the tuned local LLM: an emergency fine-tune of Gemma 4 E2B, ideally built with Google, grounded in the drive's library, numbers copied from sources, validated against a public clinical and operational benchmark.
- **Later:** the block-board hotspot app; a hub image with full Wikipedia for libraries.
