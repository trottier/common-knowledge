# AGENTS.md — Common Knowledge, v0.1

Instructions for an AI coding agent (Claude Code, Codex, Cursor, or similar) building the public GitHub repository for **Common Knowledge**: a read-only emergency USB drive mailed to every U.S. household. Read this whole file before writing anything. If this file and a request conflict, ask the human.

**Git holds only what the project writes.** Code, original text, configuration, and a pinned catalog of external sources live in git. Maps, Wikipedia, reference archives, apps, fonts, the offline AI model, and imported videos are fetched by reference at image-build time, verified by checksum, and never committed.

---

## 1. What the project is

Every household gets the same kit: a read-only USB-C drive with a whistle and compass built into its body, attached to a printed card. The drive works **with zero preparation**: on the day of an emergency, someone plugs it into a phone, taps, and it works with no internet, no app store, and no setup. Older laptops, TVs, and car stereos with only USB-A ports need an adapter, which a neighbor can lend.

**Why the design works.** Four mechanisms depend on each other, and the code must not weaken any of them:

- **Trusted sender.** An official, sealed, verifiable mailing. Hashes, the verification site, and reproducible builds (§12, §13) are what make the trust checkable.
- **Universal reach.** Every household gets the same plan; nothing is opt-in.
- **Common knowledge.** Because the mailing is public and universal, everyone knows everyone else has the same defaults. That is why every default must render identically in every edition (§14).
- **Complementary variants.** Each drive holds a different part of the library, so neighbors have a practical reason to find each other. The same scheme keeps the cost per drive down.

Design rules that every line of code and content must respect:

1. **Zero preparation.** Nothing may depend on anyone installing, downloading, or filling in anything beforehand. Core content opens in a phone's built-in Files app. The only installs allowed are optional one-tap Android installs (APKs) and double-click laptop programs.
2. **Phone-first, laptop-capable.** PDF and MP4 are the only formats the core depends on. ZIM archives, map files, apps, and the offline AI are extras.
3. **Nationally standardized.** One national design. No per-city, per-county, or per-address customization. Stable public places for every state and territory may ship; event-specific facts (which shelters are open, where water is handed out) and sensitive infrastructure never ship.
4. **Universal defaults replace coordination.** Rally point, meeting times, radio channel, mesh channels, and convener rules come from one config file and render identically everywhere.
5. **Eight variants, shuffled at random.** Every drive carries the same core. Each variant adds video libraries for three of twelve topics plus one in-depth knowledge collection. Each topic appears on exactly two variants; each collection on one.
6. **Smallest correct release first.** Prove one usable Variant 1 sample before expanding nationally or building all eight images. Ship v0.1 from existing sources, then improve the content image; the hardware stays fixed.
7. **The folders are the interface.** Design and inspect the actual files, names, sort order, and navigation in phone Files apps. A working build pipeline or desktop website does not establish a usable drive. Shared emergency instructions and defaults stay identical; generated inventories and offline-AI availability notices reflect the actual variant.

## 2. Scope of v0.1

v0.1 assembles **everything that can be built from existing sources** into eight full drive images, plus the project's own core content.

**In scope:**

- The core: START document, card, tag sheet, and "How is my drive different?" page, in English (reviewed) and Spanish (machine-translated, marked unreviewed).
- **All 15 language editions stubbed** (§9.2).
- A **road atlas** of every county and county-equivalent in every state and territory, with a latitude/longitude grid, and a **national places directory**, built from public data (§9.3, §9.4).
- **Android offline maps** for every state and territory, plus the map app (§9.5).
- **Wikipedia-family and reference archives** (ZIM), with a curated set of medical articles converted to phone PDFs for iPhones (§9.6).
- **Imported public-domain and openly licensed videos and documents**, normalized to the drive's spec, with narration and subtitle tracks stored in one file per clip (§9.8).
- **Phrasebooks**, radio and incident-command forms, and exam question pools (§9.9).
- The **mesh chat apps** (bitchat, Briar).
- The **eight in-depth knowledge collections**, populated from the catalog.
- A **capacity planner** that places every item, then an assembler that builds eight reproducible images, plus CI, releases, a verification site, and tests.

**Current milestone:** one integrated, browsable Variant 1 `sample` build using Rhode Island, inspected through the local Drive Explorer and then on actual phones. Build the real tree first; complete and inspect its folder UX before national expansion. If selected cargo remains blocked, show an explicitly incomplete inspection preview and its omissions. This is a development milestone, not a claim that all v0.1 release requirements are complete.

**Offline AI: v0.2.** The offline AI ships in v0.2, on variants 7 and 8 only (§9.7). The single integration flag is `offline_ai_enabled` in `config/variants.yaml`; do not duplicate it in `build.yaml`. v0.1 builds set `offline_ai_enabled: false` and contain no model, runner, Android AI app, bundle, or AI folder. Preserve existing research, verified outputs, and provenance for v0.2.

**Out of scope for v0.1:** shooting original videos, the offline AI (v0.2; tuning in v0.4), the block-board app, human-reviewed translations beyond Spanish, hardware procurement, and mailing.

## 3. Hard rules

**Never:**

- Invent facts, numbers, doses, frequencies, URLs, versions, sizes, licenses, or checksums. Look them up from the primary source, or write a `[[VERIFY: ...]]` marker (§10).
- Commit large binaries (anything over 5 MB: archives, APKs, models, map data, fonts, videos, images) to git. Reference them in the catalog and fetch at build time.
- Include anything whose license does not allow redistribution on a free government-distributed drive. Red Cross, Stop the Bleed, Hesperian, Khan Academy, and iFixit (noncommercial license) materials are **out** until a free emergency-use license is granted in writing; the project will request one from each. In-depth knowledge collections use only public-domain or openly licensed material that needs no permission. YouTube rips are **out**; import only files hosted by the rights holder or by Wikimedia Commons.
- Add telemetry, analytics, network calls from shipped content, or `autorun.inf`. Executables may appear only in `6_VIDEOS_AND_IN_DEPTH/*/laptop/`, `7_LAPTOP/`, `8_MESH_CHAT/`, `9_OFFLINE_AI/`, and any `android/` subfolder.
- Modify third-party files. Ship them byte-identical to the publisher's release, or regenerate them from source data with a pinned, documented pipeline.
- Ship per-locality data, event-specific shelter or distribution locations, or sensitive infrastructure (substations, water and wastewater plants, pipelines, dams, telecom sites).

**Always:**

- Keep one source of truth. Every default value is read from config, never retyped.
- Record every external item in `catalog/` with URL, version, size, SHA-256, license, attribution, and placement.
- Make builds reproducible: pinned inputs, pinned build container, fixed timestamps (§12).
- Keep pull requests small, with tests. Use Conventional Commits.

### 3.1 Development discipline

Rules for the current build machine and agent setup live in `AGENTS.local.md`, which is listed in `.gitignore` and never committed. Read it too if it exists; where it conflicts with this file, this file wins.

- **One vertical slice first.** Prepare, assemble, inspect, and test Variant 1 with one small state before extending coverage. Accept explicit variant selectors throughout preparation and assembly; preserve an all-variant mode for the later release. Do not fetch another variant's topics or collections for this milestone.
- **Make progress visible.** Keep a stable local preview folder and a loopback Drive Explorer pointing to the actual built files (§3.2). Report the exact variant, profile, source commit, completed components, omissions, and review status. A core-only preview, a component bundle, an integrated sample, and a full production image are distinct deliverables. Never present catalog-only entries or missing files as assembled cargo.
- **Preflight before expensive work.** Resolve the selected input graph, hashes, sizes, applicable rights, source availability, expected completeness, and epoch before starting long conversions. Inventory existing artifacts before rebuilding. Check all selected archive languages for known tool diagnostics before freezing a shared validator.
- **Freeze, then build.** Freeze producer code, configuration, selected inputs, tool image, and epoch for a repeat pair. Keep active producers in isolated checkouts with read-only source/cache mounts. Commit integration changes elsewhere; never edit a running producer's inputs.
- **Cache by actual dependency.** Bind each artifact to the source and configuration it actually consumes, selected input pins, tool/environment identity, and producer version. An unrelated catalog addition or review-note edit must not invalidate every map, video, or document. A change to selected attribution or output-affecting code must invalidate the affected artifact. Prove these boundaries with focused tests.
- **Reuse honestly.** Reuse complete, checksum-verified artifacts under their recorded recipes and source epochs. Retain the source commit and dependency manifest needed to reproduce them. Never give an old artifact a new recipe/hash, change `complete: false` to true, or hide an epoch/input mismatch. Pin one prepared artifact and reuse it across variants rather than regenerating it per variant.
- **Separate technical completeness from human review.** A successfully generated draft can be technically complete while still unreviewed. Rejecting unrelated records in another state must not mark an otherwise complete Rhode Island output incomplete. Missing required local data, broken references, or failed validation must still block technical completeness.
- **Keep rights and release gates precise.** Development text may retain visible draft/VERIFY markers. This does not waive unknown rights, excluded licenses, missing permissions, corrupt inputs, or unsafe output. Distinguish a documented build-only use grant from permission to redistribute the original input. Never invent a broader license. Named human review, source-release obligations, and publication gates remain in force for release.
- **Do not hide blockers.** If a complete sample cannot be assembled, produce an explicitly incomplete local inspection preview and an exact blocker inventory. Do not call it a completed sample, publish it as a release, or silently omit selected cargo. Any preview-only behavior must be explicit and must not weaken normal full/release checks.
- **Test at the right stage.** Use a fast English, single-county loop for map, folder, and core-layout changes, with the relevant focused checks. Inspect that result in Drive Explorer before an all-edition render or a wider map run. Freeze the coherent milestone's selected inputs, producers, configuration, environment, and epoch before full CI, required language/RTL checks, and reproducibility checks. Keep one active milestone integration PR at a time. Build a browsable tree before a disk image; defer expensive compression and national repeats until the layout and inputs are stable. Existing CI triggers and full/release gates remain in force.
- **Keep verification work scoped.** Defer new image-verifier tool development during the current Drive Explorer milestone. Keep existing checksum, manifest, input-verification, reproducibility, verification-site, and release checks; this deferral does not waive them or turn a browser preview into verification of an image.
- **Persist within scope.** Continue useful authorized work until the milestone is complete or actually blocked. Keep `docs/release-review.md` current; it is a handoff, not an excuse to stop while automatable milestone work remains. Do not invent human approvals or contact rights holders without explicit authorization.
- **Tooling.** Use Python 3.12 and `uv`. Preserve existing runtimes, lockfiles, and test frameworks; document concrete compatibility exceptions such as the native MapLibre Node ABI.

### 3.2 Local Drive Explorer

Drive Explorer is a development inspection website over a real built folder tree. Bind its server to loopback, and keep file access read-only and confined to the selected preview root. Resolve paths safely, reject traversal and escapes through symlinks, and expose only intended preview files. It does not replace the drive's ordinary Files-app interface.

- Browse actual folders with breadcrumbs, clear sort order, complete filenames, and file sizes. Phone-size presets must let a reviewer inspect long locality/ZIP filenames without losing their full text; preserve verified ZIP gaps and ranges exactly. Show human-readable sizes and make exact byte counts available.
- Open PDFs with the browser's native PDF viewer, videos with native playback controls, and text as inert escaped text. Use the actual files, rather than fabricated pages, invented metadata, or screenshots standing in for missing cargo. Unknown formats remain clearly identified files.
- APKs, installers, launchers, scripts, disk images, and other binaries stay inert in the website. Do not execute them, offer an installation flow, or expose a write/upload action. Browser navigation must not launch bundled applications.
- Keep the selected variant/profile, source provenance, development/review status, missing cargo, and held components visible in the inspection interface. A partial tree must say it is incomplete; holding a file is not permission to silently omit its selected inventory record or weaken normal assembly checks.
- Phone-size presets exercise layout only. A desktop browser's PDF renderer, available RAM, local disk, and input controls do not reproduce a phone's built-in viewer or USB access. Record physical-device results separately; do not claim handset certification or the phone-coverage target from this preview.

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
| Offline AI | `llamafile` and/or `llama.cpp` builds | Apache-2.0 / MIT |
| Video | `ffmpeg` | LGPL/GPL (tool only) |
| APK checks | `apksigner` | Apache-2.0 |
| Disk images | `dosfstools`, `mtools`, `zstd` | GPL/BSD (tools only) |
| Lint, tests | `ruff`, `pytest` | MIT |

## 5. Repository layout

```
common-knowledge/
├── AGENTS.md  (copy to CLAUDE.md for Claude Code)
├── AGENTS.local.md          # machine-specific rules; in .gitignore, never committed
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
  structures:   { category: infra, title: "Structures, fire, and search" }
  comms:        { category: infra, title: "Comms and information" }
  transport:    { category: infra, title: "Transport and evacuation" }
  convening:    { category: civic, title: "Convening and liaison" }
  welfare:      { category: civic, title: "Welfare and reunification" }
  legal:        { category: civic, title: "Legal, money, and recovery" }
  psychosocial: { category: civic, title: "Psychosocial, kids, and morale" }
offline_ai: [7, 8]  # from v0.2; allocation and integration flag have one source of truth
offline_ai_enabled: false  # v0.1; no model, app, runner, bundle, or AI folder
collections:   # in-depth knowledge, one per variant
  howto_1:    "How-to library, part 1"
  howto_2:    "How-to library, part 2"
  laptop_map: "Interactive map for laptops"
  med_lib:    "Medical library"
  repair:     "Repair and engineering"
  simplewiki: "Simple English Wikipedia and travel guides"
  school:     "School lessons for disrupted schooling"
  morale:     "Public-domain books, music, and games"
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

Invariants (tested): each topic on exactly two variants; each variant has one body, one infrastructure, and one civic topic; collections unique; when `offline_ai_enabled` is true, the offline AI is on exactly the variants listed in `offline_ai`; when false, no variant contains AI payloads. `ck coverage` prints findability, where *k* is the number of variants carrying an item and *n* the number of nearby homes: P = 1 − (1 − k/8)^n.

### `config/languages.yaml`

Fifteen editions. Preserve the publisher's 2026-10-31 decision: retain these editions, ordered by 2025 ACS B16001 limited-English-proficiency point estimates within that selection. This is a documented selection exception, not a claim that these are the fifteen highest-ranked individual languages. English remains first; both Chinese scripts share one Census language group. Preserve the pinned audit and the Bengali/Japanese selection exception in `docs/language-selection.md`.

```yaml
# status: full | machine | stub; retained selection, ordered by the pinned ACS audit
- { code: en,      name: "English",          script: Latn, dir: ltr, font: noto_sans,      status: full }
- { code: es,      name: "Español",          script: Latn, dir: ltr, font: noto_sans,      status: machine }
- { code: zh-Hans, name: "简体中文",          script: Hans, dir: ltr, font: noto_sans_sc,   status: stub }
- { code: zh-Hant, name: "繁體中文",          script: Hant, dir: ltr, font: noto_sans_tc,   status: stub }
- { code: vi,      name: "Tiếng Việt",       script: Latn, dir: ltr, font: noto_sans,      status: stub }
- { code: ko,      name: "한국어",            script: Kore, dir: ltr, font: noto_sans_kr,   status: stub }
- { code: tl,      name: "Tagalog",          script: Latn, dir: ltr, font: noto_sans,      status: stub }
- { code: ar,      name: "العربية",          script: Arab, dir: rtl, font: noto_sans_arabic, status: stub }
- { code: ht,      name: "Kreyòl ayisyen",   script: Latn, dir: ltr, font: noto_sans,      status: stub }
- { code: ru,      name: "Русский",          script: Cyrl, dir: ltr, font: noto_sans,      status: stub }
- { code: pt,      name: "Português",        script: Latn, dir: ltr, font: noto_sans,      status: stub }
- { code: fr,      name: "Français",         script: Latn, dir: ltr, font: noto_sans,      status: stub }
- { code: fa,      name: "فارسی",            script: Arab, dir: rtl, font: noto_sans_arabic, status: stub }
- { code: pl,      name: "Polski",           script: Latn, dir: ltr, font: noto_sans,      status: stub }
- { code: hi,      name: "हिन्दी",            script: Deva, dir: ltr, font: noto_sans_devanagari, status: stub }
```

### `config/build.yaml`

```yaml
version: "0.1.0"
volume_label: "EMERGENCY"
volume_id: "0C0FFEE0"
site_base_url: "https://trottier.github.io/common-knowledge/"
source_date_epoch: "[[VERIFY: set at release]]"
pdf:
  max_file_mb: 10          # provisional engineering guardrail; MB = 1,000,000 bytes
  target_phone_coverage: 0.95
  # Validate file size AND rendering memory/interaction before making a coverage claim.
profiles:
  dev:    { third_party: none,   image_size_mib: 256 }                # CI on every push
  sample: { third_party: sample, image_size_mib: 4096 }               # Variant 1 + Rhode Island first; no AI in v0.1
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

- Take URLs, versions, sizes, and checksums **only** from the publisher's official pages or checksum files. Where a publisher gives no checksum, download over HTTPS, verify (signer certificate for APKs, `zimcheck` for ZIMs), and pin the hash in a reviewed pull request.
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
| Gemma 4 E2B, 4-bit GGUF | llm | [[VERIFY]] | Apache-2.0 [[VERIFY: confirm on the model card]] | variants 7 and 8 only (`offline_ai`, §8) |

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
4. The offline AI is off in v0.1 and adds no payload or dependencies. From v0.2 it goes on variants 7 and 8 only (k = 2: within five homes 76% of the time, within ten 94%). Keeping it off most drives lets anyone who does not want it trade for a drive without it; the drive number tells them which they have. Never make it universal without a human decision recorded in the catalog.
5. Medical references are universal up to about 1.5 GB; the rest goes to `med_lib`.
6. Everything else fills the in-depth knowledge collections; what does not fit is `hub_only`.

`ck assemble --variant N` then builds each variant tree from the plan.

## 9. Pipelines

### 9.0 Phone Files UX and PDF performance

- Treat the actual folder tree as the primary interface. Test finding, opening, returning, copying, and sharing files in built-in iPhone and Android viewers, directly from the drive with networking off. A desktop preview is useful but is not a phone acceptance test.
- Use recognizable place/content names, short paths, clear sort order, and useful PDF titles, bookmarks, and page locators. Keep identifiers, source hashes, and build machinery out of normal navigation. Do not require a website, custom reader, cross-file PDF link handler, or a phone's ability to search every PDF on an external drive.
- The initial per-file PDF guardrail is **10 MB**, an engineering starting point rather than a proven phone-memory threshold. Read it from `config/build.yaml`; do not repeat the number in generators. The goal is usable PDFs on **95% of phones**, not merely small downloads. Tune the MB limit and rendering limits from evidence while retaining enough map/content detail to be useful.
- File bytes alone do not predict viewer memory. Measure page count, largest decoded image, concurrently rendered pages, vector/path and label complexity, peak memory where measurable, cold-open time, zoom/pan responsiveness, and repeated page switching. A compressed image can require a much larger decoded pixel buffer; see the [Android memory guidance](https://developer.android.com/topic/performance/memory/guide/bitmaps).
- Test older and low-memory handsets as well as current phones, using their built-in Files/PDF viewers and real USB access. Record device, OS, viewer, file, file MB, test procedure, results, and measurement limitations. A few passing devices do not prove 95% installed-base coverage. Any numerical coverage claim needs dated, representative evidence and a documented denominator.
- Apply the PDF budget to every shipped PDF, including overviews, directories, imported documents, and copy indexes. Split or regenerate through a pinned, license-permitted pipeline when necessary; do not silently blur maps, omit content, alter third-party originals, or ship an oversized file without resolving the budget. Android `.obf`, ZIM, and laptop tile files have separate format-specific budgets.
- Ordinary instructions remain readable without zoom. Maps are deliberately designed for pinch-zoom and panning; preserve crisp road geometry, road names, route shields, and navigation context at the intended detail scale. Test this behavior rather than assuming it from DPI or file size.

### 9.1 Core documents (START, card, tags)

- Markdown → HTML (Jinja2 templates) → PDF with WeasyPrint.
- **Phone PDF:** 90 mm × 160 mm pages, base type at least 12 pt, one column, tappable contents page, PDF bookmarks for every heading. **Print PDF:** US Letter.
- **Card:** half-letter, two-sided, attached to the drive. The front holds the rally rule, meeting times, convener rule, radio channel, mesh channels, write-in blanks (rally point, out-of-area contact, household medications), and three QR codes (videos page, state emergency agencies page, verification page). The back is a large OK/HELP placard and four pictures showing how to open the drive on an iPhone and on an Android phone. The rally-point blank carries the hint "e.g., your building's front entrance" for apartment dwellers. The back also carries one line listing what is on every drive, generated from `variants.yaml` and the plan so it stays accurate, for example: "On every drive: playbooks in 15 languages · how-to videos · maps of every state and territory · medical reference · mesh chat apps. Plus one numbered collection: compare numbers with neighbors." From v0.2 the line adds: "Drives 7 and 8 also include an offline AI assistant; trade with a neighbor if you'd rather not have one."
- **Tags:** US Letter label sheet: GAS — ¼ TURN — WRENCH HERE; WATER MAIN; MAIN BREAKER; MEDS IN FRIDGE.
- The card line and every inventory describe what the build actually contains; never mention the offline AI in a build that lacks it.
- The "How is my drive different?" page is generated from `variants.yaml` and the plan. It first lists what each variant holds (its three topics, its in-depth knowledge collection, and, from v0.2, the offline AI on variants 7 and 8), then explains why drives differ: complementary content gives neighbors a reason to find each other and keeps the cost per drive down.
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
10. The offline AI (from v0.2): which drives carry it (7 and 8), what it is, how to start it, and why the printed cards win when they disagree. On other variants this section says only that drives 7 and 8 carry it. v0.1 omits this section.
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

- **Sources** (confirm each endpoint, license, and freshness):
  - Public schools: National Center for Education Statistics (EDGE school locations).
  - Public libraries: Institute of Museum and Library Services, Public Libraries Survey outlets.
  - Hospitals, urgent care, pharmacies, fire stations, police stations, post offices: OpenStreetMap via the Geofabrik U.S. extract filtered with `osmium tags-filter` (ODbL attribution).
  - Broadcast stations: FCC licensing data.
  - NOAA Weather Radio transmitters: National Weather Service station list.
  - County hazard profiles: FEMA National Risk Index county table.
  - State emergency agencies: an official federal list [[VERIFY: source]].
- **Output:** bounded phone-friendly places PDFs alongside each county or split-area map, sorted by category, then name. A state-level lookup may index these files; no giant state PDF is required for navigation. Each entry gives name, address, coordinates, and map file/page plus grid square. Each source shows an "as of" date, and every page says "may help; not confirmed open." Keep print editions only where useful and within the PDF budget.
- **Exclusion list in code:** substations, power plants, water and wastewater plants, pipelines, dams, telecom sites, government buildings beyond the categories above. A test fails if any excluded tag appears.

### 9.4 Road atlas: county-first files, useful zoom, and postal lookup

- **Inputs:** pinned Protomaps/OpenStreetMap basemap data; Census county/county-equivalent boundaries; Census places and county subdivisions where needed for towns; directory points; and documented ZIP/locality lookup sources. Confirm dates, rights, exact sizes, and hashes in the catalog before use.
- **Folder and leaf names:** `3_MAPS_AND_PLACES/CA/San Mateo County/South SF ZIP-LABEL.pdf` illustrates the structure. `ZIP-LABEL` is a placeholder for verified ZIP codes, not literal output. The locality/ZIP label is the leaf PDF name, not an extra folder. State and territory postal abbreviations and readable county names are navigation; FIPS and other machine IDs stay in metadata unless needed for disambiguation.
- **County-first default:** make one detailed PDF per county when measured file size, memory, interaction, and legibility permit. The county is the maximum geographic group, apart from useful edge overlap. One PDF may contain several atlas-scale map pages, a locator index, and bookmarks; do not shrink a whole county onto one page just to keep one file.
- **Split only when useful:** if a county exceeds the performance or usability budget, split it into recognizable locality/ZIP-named PDFs. Group nearby areas within the county using geography, connected roads, extent, settlement/road density or verified population, and label complexity. Combine small neighboring areas where helpful; split dense urban areas or geographically large regions where needed. Do not merge whole counties merely because a combined file fits. Keep grouping deterministic and record its inputs and decisions.
- **ZIP labels:** use verified codes and compact only genuinely consecutive codes into ranges. Never turn a minimum and maximum into a range that implies unverified intervening ZIPs. Preserve the complete code list inside the PDF/index, and use documented shortening/grouping when a filename would exceed the FAT path budget. Include unincorporated areas, county subdivisions, and places that do not map neatly to incorporated cities.
- **Postal geography:** Census ZCTAs approximate ZIP geography; they are not a complete, current USPS delivery directory. Label the source/date and limitation. Preserve one-to-many, cross-county, and cross-state relationships. Do not assign every ZIP to one county or blindly join older county IDs to newer county-equivalent boundaries. See [Census ZCTA guidance](https://www.census.gov/programs-surveys/geography/guidance/geo-areas/zctas.html).
- **Published atlas conventions:** use documented road-atlas practice: coherent regional sheets at useful scales, overlap, a sheet locator, adjacent-sheet/file references, and larger-scale urban detail. [Benchmark's Idaho atlas](https://www.benchmarkmaps.com/product/idaho-road-recreation-atlas/) explicitly documents overlap and separate regional/metro scales; its [sheet locator](https://www.benchmarkmaps.com/wp-content/uploads/2020/10/Idaho-Atlas-Landscape-Map-Page-Grid.jpg) and [sample spread](https://www.benchmarkmaps.com/wp-content/uploads/2020/10/ID-A_ls_900_rgb.jpg) illustrate the navigation. Follow the conventions, not copyrighted cartography. Do not claim one universal U.S. atlas scale. Document Common Knowledge's own selected scales, overlap, and thresholds.
- **Overview versus detail:** each county folder gets a small zoomed-out overview identifying the detailed files and major routes. Account for all included public-place points in that county using uncluttered markers, an index, and companion places pages; complete POI coverage does not require printing every label on the overview. Every overview marker/index reference must resolve to the corresponding place entry. Keep exhaustive names, addresses, and other POI details in the bounded places directory. Detailed maps prioritize usable roads, labels, route continuity, and orientation; do not crowd them with a directory legend or hundreds of numbered points.
- **Rendering:** the existing MapLibre PNG path is a starting implementation, not a zoom-quality guarantee. Prefer crisp vector roads/text where practical, or bounded raster sheets with demonstrated zoom quality. Merely increasing PNG dimensions can multiply decoded memory. Benchmark the selected renderer before committing to a national run; pin the renderer and environment.
- **On every detail sheet:** latitude/longitude labels in decimal and degrees-minutes-seconds, a grid, scale bar, north/orientation cue, source date, ODbL attribution, locator, and clear continuation references. Geographic sheets may overlap county edges to preserve route continuity. Every cross-file convenience link also has a readable filename/page reference for viewers that do not follow local links.
- **Budgets and acceptance:** enforce the shared per-PDF MB limit plus measured rendering/interaction limits and `atlas.max_total_bytes`; the existing national target is about 3.5 GB. Preserve coverage and useful scale when splitting rather than silently reducing detail. Demonstrate one complete Rhode Island county before expanding to all counties. Split a dense area only when measured file, rendering, interaction, or legibility limits require it; do not force an extra split merely to create a demonstration. Exercise necessary splitting and its navigation with focused fixtures. National completeness tests follow the new county/file index, not the obsolete one-PDF-per-state layout.

### 9.5 Android offline maps

- **Path A, prebuilt:** OsmAnd's official per-state and per-territory map files, if OsmAnd's terms allow redistribution [[VERIFY: OsmAnd terms and per-state sizes from its index]].
- **Path B, roads and places:** Geofabrik state extracts filtered with `osmium` to roads, places, and directory categories, then converted to OsmAnd's format with its map creator. Large states need splitting; see `docs/build-machine.md` for memory.
- Choose by size with the planner. Default to Path B if Path A overflows or its terms are unclear.
- Ship the OsmAnd APK. Write and phone-test a one-page how-to for importing a state's map file into OsmAnd from the drive [[VERIFY: exact import flow on current Android]].

### 9.6 Reference archives and iPhone medical PDFs

- ZIMs come from the catalog, are verified with `zimcheck`, and land in the placed folder with Kiwix readers alongside.
- `pipelines/zim2pdf`: reads the article list in `catalog/medpdf_topics.yaml` (start with about 150 high-yield topics from WikEM and WikiMed) using `python-libzim`, renders phone PDFs with CC BY-SA attribution and article dates, and places them in `5_MEDICAL_REFERENCE/pdf/`. These serve iPhones, which cannot install Kiwix offline.

### 9.7 Offline AI (v0.2; variants 7 and 8 only)

**Not part of v0.1. Do not work on or select this integration for the current Variant 1 milestone.** Keep existing artifacts and research with their actual historical recipes. The specifications below describe the v0.2 integration, not current sample dependencies.

- **Model selection criteria,** recorded in `catalog/llm.yaml` with the reasoning:
  - Open weights under Apache-2.0 or MIT; avoid custom licenses with use restrictions unless legal approves.
  - Strong multilingual coverage of the 15 editions.
  - Four billion parameters or fewer. For Gemma 4 E2B, use effective parameters as previously clarified by the publisher; the separate file-size limit still applies.
  - 4-bit GGUF of 2.5 GB or less.
  - Context window of 32K tokens or more.
  - Primary candidate: Gemma 4 E2B (Apache-2.0, built for on-device use; v0.4 plans an emergency fine-tune of it, ideally with Google). Alternates: current Qwen small models (Apache-2.0) and Phi mini models (MIT) [[VERIFY: latest versions, licenses, GGUF files, and checksums]].
- **Laptop:** `llamafile` (or `llama.cpp` server) with the GGUF stored as a separate file, because Windows cannot run executables over 4 GB. Launchers: `Start Offline AI - Windows.bat`, `Start Offline AI - Mac.command`, `Start Offline AI - Linux.sh`. Each starts the local server on `127.0.0.1` and opens the browser.
- **Android:** an open-source app that loads a local GGUF file [[VERIFY: candidate app, license, current APK, and checksum]], plus a how-to.
- **Grounding:** a system prompt in `pipelines/llm/system_prompt.md` that:
  - instructs short answers in the user's language,
  - requires pointing to the START section by title,
  - forbids inventing doses and other numbers,
  - says to follow the printed cards when in doubt.

  If the context window allows, it also includes the START text for that language.
- **Warning:** on the launcher page and in START: "This assistant runs only on your device and can be wrong. If it disagrees with a card or video, follow the card."
- No tuning and no evaluation claims in v0.2.

### 9.8 Imported videos and documents

- Import only files hosted by a U.S. federal agency (public domain, confirmed per item) or Wikimedia Commons under CC0, CC BY, or CC BY-SA. Record the proof URL per item.
- Normalize videos to the drive spec:
  - Vertical 480×854 where the source allows (otherwise letterbox to fit), 30 fps.
  - H.264 main profile, `yuv420p`, about 600 kbps, `-movflags +faststart`.
  - **One MP4 per clip; the picture is stored once.** Never burn text into the picture. Each language is an extra track in the same file: AAC mono narration (about 32–48 kbps) and a `mov_text` subtitle track, each tagged with its ISO 639 language code.
  - Track order: English first, Spanish second, then the other editions in `languages.yaml` order. Many default Android players, TVs, and cars play only the first track, so English must be the default.
  - Imported videos keep their original audio as the first track and add subtitle tracks where translations exist; the full 15-language narration applies to the original videos in v0.2.
- **Catalog order.** Within each list, put practical, little-known fixes first (for example a box-fan air purifier, or keeping insulin cool with a clay-pot evaporative cooler). These are what people remember and share.
- Federal documents go in by topic, or universal if critical, with the original title and agency.

### 9.9 Phrasebooks, forms, and question pools

- Wikivoyage phrasebooks for each edition's language (CC BY-SA 4.0), taken from the Wikivoyage ZIM or a pinned dump, rendered as phone PDFs.
- FEMA incident-command forms and radio exam question pools go into the comms topic, subject to confirmed licenses.

## 10. Content rules

- **Naming.** In all user-facing text, call the model the "offline AI"; never "LLM" or "language model".
- **Plain language.** Short sentences, one action per line, imperative mood, roughly 6th-grade reading level. Use the Oxford comma.
- **When not to.** Every action states when not to do it.
- **No help is coming.** Every medical and rescue protocol ends with a branch for when 911 does not answer.
- **Sources.** Every factual claim cites a source id from `content/sources.yaml`. Prefer primary U.S. federal sources. Federal text is public domain; images on federal sites may not be.
- **VERIFY markers.** Anything unconfirmed is written `[[VERIFY: ...]]`. Dev builds highlight markers in yellow. **Release builds fail if any remain,** in content, config, or catalog.
- **Tone.** Calm and practical. State what to do, not how bad things could get; no alarming imagery or language.
- **Political neutrality.** No partisan content, no commentary on officials, parties, or policy debates, and no content selected for a political point of view. The drive must be acceptable to any administration that might publish it.
- **Review status.** Content front matter carries `status: draft | reviewed | machine`, `reviewer:` and `reviewed_on:`. Medical, legal, and radio sections need a named human reviewer for release. The agent never sets `reviewed`.

## 11. Drive layout

```
/README.TXT                 # every edition: "Open 1_START"
/VERIFY.TXT                 # version, variant, verification URL
/MANIFEST.SHA256            # every other image file; the manifest's own hash is published outside
/1_START/<edition folder in its own script>/   # START or quick start, phone + print
/2_VIDEOS/                  # imported critical videos (universal), android/VLC.apk
/3_MAPS_AND_PLACES/
    0_FIND_A_MAP.pdf
    <STATE>/<County>/
        0_OVERVIEW.pdf
        <County and verified ZIP labels>.pdf        # default: one detailed county PDF
        <Locality and verified ZIP labels>.pdf      # only when the county needs splitting
        <Area> - Places.pdf                         # bounded companion directory
    android/OsmAnd.apk, maps/<state>.obf, HOW_TO.pdf
/4_PHONE_PACK/              # phone PDFs + card, copy-ready; 0_WHAT_TO_COPY.pdf indexes every shareable item on this drive with its size
/5_MEDICAL_REFERENCE/       # ZIMs, pdf/, android/Kiwix.apk
/6_VIDEOS_AND_IN_DEPTH/
    topics/<topic>/         # this variant's three video libraries
    in_depth/<collection>/  # this variant's in-depth knowledge (laptop/ subfolder may hold executables)
/7_LAPTOP/                  # static HTML version, Kiwix desktop, map viewer launcher if placed here
/8_MESH_CHAT/               # bitchat, Briar, LICENSES/, SOURCE.TXT
/9_OFFLINE_AI/              # absent in v0.1; from v0.2, variants 7 and 8 only
/BACKUP/                    # second copy of 1_START and 4_PHONE_PACK, FAT hidden attribute
```

File names must be FAT-safe: none of `\ / : * ? " < > |`, path length under 200 characters. Angle-bracket names in this diagram are placeholders, never literal output. Use numbered entry/overview/index files for sort order; map leaf PDFs use recognizable area and verified ZIP names. Folder names may use any script, because FAT long names are UTF-16.

## 12. Assembler, images, and reproducibility

- All builds run inside `Dockerfile.build`, pinned by base-image digest. Every tool version is recorded in the image's `VERIFY.TXT`.
- `ck image --variant N --profile P`:
  1. Sets every file's mtime to `SOURCE_DATE_EPOCH` with `TZ=UTC`.
  2. Runs `mkfs.fat -F 32 -n EMERGENCY -i 0C0FFEE0 -C <img> <KiB>`.
  3. Creates directories with `mmd` and copies files one by one in sorted order with `mcopy -m -Q` (`MTOOLS_SKIP_CHECK=1`).
  4. Runs `mattrib +h` on `/BACKUP`.
  5. Writes the manifest inside the image, covering every other file. Publish the manifest's own SHA-256 and the image SHA-256 outside the image; do not attempt a circular self-hash.
  6. Compresses with `zstd -19` and hashes the result.
  7. Checks the listing with `mdir -/`.
- **Reproducibility test:** two clean builds of variant 1 in the `sample` profile must produce identical image hashes. Normalize any nondeterminism (PDF IDs, archive timestamps) or document it in `docs/reproducibility.md` with an `xfail` test and an issue link.
- **Build machine for `full`** (`docs/build-machine.md`): the recommended large-build target is Linux x86-64, at least 16 cores, at least 64 GB RAM, at least 1 TB of free SSD, Java 17+, and Node 20+. Smaller machines can build the `sample` profile with bounded jobs; a large machine is not a prerequisite for the sample milestone. Cache downloads by SHA-256 and generated artifacts by their verified input/recipe manifests.

## 13. CI, releases, and distribution

- **`ci.yml`** (every push and pull request): ruff, pytest, `dev` profile build of all PDFs and variant 1, and an RTL rendering test. Upload artifacts.
- **`sample.yml`** (on demand first; schedule only when the selected sample is stable): prepare one small state's county maps, directory, Android map, WikEM, and selected apps for Variant 1. Do not fetch AI dependencies in v0.1. First prove Variant 1's browsable tree, phone UX, image, and reproducibility pair; extend to Variant 3 and broader CI coverage afterward. Full release checks remain global.
- **`release.yml`** (tag `v*`): fail on any VERIFY marker or unreviewed medical, legal, or radio content. Publish to the GitHub Release: the PDFs, `dev`-profile images, the catalog lock, `SHA256SUMS`, and GPL source archives. Each file must be under 2 GB.
- **Full images** are built from the tagged commit on the build machine with `make full`. They are too large for GitHub Releases. Publish their hashes on the Pages site; hosting (object storage, BitTorrent with web seeds, or both) is a human decision [[VERIFY: hosting choice]]. Because every input is pinned, anyone can rebuild and check the hashes.
- **`pages.yml`:** the verification site, with every image hash, how to check with `sha256sum`, `shasum -a 256`, or `certutil -hashfile`, the catalog with licenses and attributions, and links to the PDFs.

## 14. Tests (minimum)

- Config and catalog schemas validate; every catalog item has license, proof URL, SHA-256, size, and placement.
- Variant invariants hold; `ck plan --profile full` fits every variant within capacity.
- In v0.1 builds, no selected graph or assembled variant contains AI payloads or an AI folder. From v0.2, `9_OFFLINE_AI/` exists only on variants 7 and 8; card and inventory wording follows configuration and actual placement.
- Every default appears verbatim in the card and START HTML for every edition.
- All 15 editions exist with folder, quick start, and README line; RTL editions render correctly.
- Every citation id exists; release mode fails on any VERIFY marker.
- The directory contains no excluded categories. The pinned 2025 Census snapshot has 3,235 counties/county-equivalents (the 50 states, DC, Puerto Rico, and the island areas); the national map index covers them all, including counties split across several PDFs. Grid labels and every sheet continuation parse and resolve.
- Every shipped PDF fits the configured MB budget; map fixtures cover county-wide files, necessary locality splits, ZIP gaps, cross-boundary relationships, unincorporated areas, and FAT-safe leaf names. Phone rendering and navigation results are recorded separately from byte-size checks.
- A selected-variant preparation graph excludes other variants' topics/collections and the offline AI. Verified cache reuse preserves the original recipe, inputs, complete flag, and epoch; unrelated catalog edits do not invalidate unaffected artifacts.
- Every video has one picture track, English as its first audio track, and audio and subtitle tracks tagged with valid language codes; no text is burned into new renders.
- File names are FAT-safe; no executables outside allowed folders; no `autorun.inf`.
- Drive Explorer lists actual files, preserves full locality/ZIP filenames and sizes at phone widths, previews PDF/video/text without executing binaries, rejects paths outside its preview root, and clearly labels incomplete development trees. Its tests do not count as physical-phone acceptance.
- The manifest matches the image; the reproducibility test passes in `sample`.

## 15. Manual phone and laptop checklist (`docs/phone-test-checklist.md`)

Devices: an iPhone with USB-C, an iPhone with Lightning plus an adapter, a recent Pixel, a budget Samsung, a budget Motorola, and Windows, Mac, and Linux laptops, including one with only USB-A ports (via a USB-C to USB-A adapter). Check that:

- The drive mounts; phone PDFs open; contents links and bookmarks work; text is readable without zooming.
- Find an area's map through state, county, and readable ZIP/area PDF names using the phone Files app. Check the county overview, sheet locator, neighboring-sheet references, and a cross-county ZIP case. Open and pan/zoom the detailed map from the drive; roads and labels remain useful. The Compass coordinates locate the user on the grid. Record cold-open, interaction, and memory evidence for older and low-memory devices; do not infer 95% coverage from the minimum checklist alone.
- On Android, OsmAnd installs and a state map imports and shows a live GPS dot offline.
- Kiwix opens WikEM on Android and on laptops; the medical PDFs open on iPhone.
- bitchat connects two Android phones with all networking off; Briar shares itself offline.
- A video plays in English by default on every device; the iPhone player's menu switches to Spanish audio and subtitles; VLC does the same on Android.
- From v0.2: on variant 7 or 8, the offline AI launcher starts on each laptop OS and answers in English and Spanish; the Android app loads the model on a phone with at least 6 GB of RAM. This does not block the v0.1 Variant 1 milestone.
- The phone pack copies to a phone and sends to a second phone by AirDrop or Quick Share.

## 16. Work order and current milestone

**Work toward one reviewable result before expanding breadth.** The sequence below remains the overall roadmap, not a requirement to create a separate PR for every research packet. Keep PRs small and coherent, with one active milestone integration PR.

Current order:

1. Adopt these instructions, preserve earlier explicit publisher decisions, and freeze the Variant 1/Rhode Island sample scope with AI disabled.
2. Settle and inspect the county-first map folder/leaf naming and phone PDF performance contract. Use published atlas conventions and verified postal/locality data; test one complete county, and split a dense area only when measured limits require it. Keep split-navigation fixture coverage without forcing a production split.
3. Inventory the exact selected sample graph and reuse ready, verified artifacts. Resolve only sample-critical missing inputs, hard rights questions, or technical blockers; preserve an explicit inventory for deferred items.
4. Build the actual browsable tree and expose it through the loopback Drive Explorer, with phone-size presets, full filenames, file sizes, and native file previews. If the tree is incomplete, show its exact omissions and blockers. Inspect actual files on phones before expanding the renderer or starting a national build.
5. Build and verify one Variant 1 sample image, then repeat cleanly at the frozen recipe/epoch. Compress and publish development artifacts only through the appropriate gates.
6. Expand the proven pipeline to national coverage, then the remaining variants. The offline AI follows in v0.2; it is not a dependency of Variant 1.

Overall implementation roadmap:

1. Scaffold, licenses, governance files, `Dockerfile.build`, an empty `ck` CLI.
2. The four config files, pydantic models, `ck coverage`, and invariant tests.
3. Templates and CSS; one English section rendered to phone and print PDFs; RTL test fixture.
4. English START sections with sources and VERIFY markers; card; tags; "How is my drive different?" page.
5. Catalog schema, `ck fetch` with verification, the candidate items as VERIFY entries, and `THIRD_PARTY.md` generation.
6. The planner and `ck assemble`, with dev-profile images, manifest, and CI.
7. Language editions: Spanish full, 13 stubs, fonts via the catalog.
8. Directory pipeline (one small state first, then all).
9. Atlas pipeline (one small state first, then all).
10. Android maps pipeline (Path A or B per the planner).
11. ZIM placement and the zim2pdf medical PDFs.
12. v0.2: offline-AI selection notes, launchers, Android app entry, system prompt, and placement on variants 7 and 8 only.
13. Imported videos (multi-track audio and subtitles, VLC entry) and documents, phrasebooks, forms.
14. Sample workflow, reproducibility test, release and Pages workflows, build-machine docs.

Keep `docs/release-review.md` current, listing remaining VERIFY markers, actual rights/permission questions, and sections needing named human review. Do not invent approvals or call a preview a release. Continue automatable work on the current milestone; when genuinely blocked, hand over concrete artifacts and the smallest exact decisions or reviews needed. Offline-AI work belongs to v0.2, not the Variant 1 blocker list.

## 17. Definition of done for v0.1.0

- `make full` on the build machine produces eight images that fit capacity, with published hashes; two clean builds match.
- CI and sample workflows are green; the dev-profile release is on GitHub with PDFs and GPL sources.
- All 15 editions exist; English is reviewed; Spanish and the stubs are marked as machine translations.
- No VERIFY markers remain; every catalog item has a confirmed license and proof URL; legal has signed off on flagged items.
- The phone and laptop checklist is complete on at least three phones and two laptop operating systems. PDF/map performance budgets have representative device evidence; describe the 95% goal as a target until the claimed population coverage is actually supported.

## 18. Roadmap after v0.1 (context only)

- **v0.2:** original vertical how-to videos (the 50 critical clips), narrated and subtitled in all 15 languages, replacing imports where better; the offline AI, an untuned base model, on variants 7 and 8 (§9.7).
- **v0.3:** reviewed translations for all editions.
- **v0.4:** the tuned offline AI: an emergency fine-tune of Gemma 4 E2B, ideally built with Google, grounded in the drive's library, numbers copied from sources, validated against a public clinical and operational benchmark.
- **Later:** the block-board hotspot app; a hub image with full Wikipedia for libraries.
