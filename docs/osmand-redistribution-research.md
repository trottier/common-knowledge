# OsmAnd redistribution alternatives

No qualifying replacement APK was established in this research. The selected
5.4.11 application and source remain on their existing rights, permission,
source-closure, and human-review holds. No selection, permission status, third-party
file, or APK was changed. The prior [provenance audit](osmand-provenance.md) covers
the official download and signer. This investigation extends the asset and
source-build evidence, recorded in [machine-readable research](evidence/osmand-asset-research.json).

## Publisher and F-Droid builds

The publisher's [free releases](https://osmand.net/docs/versions/free-versions/)
and [nightly channel](https://osmand.net/docs/versions/nightly_versions/) identify
free-of-charge downloads, without offering an asset-free rights grant. Its
[Android build guide](https://osmand.net/docs/technical/build-osmand/how-to-compile-the-android-version/)
documents `androidFull` as the OsmAnd~ flavor used for F-Droid without Google
Play services. At the selected source commit, `androidFull`, `nightlyFree`, `gplayFree`,
`gplayFull`, and `huawei` all inherit the main resource sets and external-resource
collection tasks. No separate asset-free flavor was found in that configuration.
Choosing the legacy renderer also does not remove the shared application UI.

[F-Droid's OsmAnd~ page](https://f-droid.org/en/packages/net.osmand.plus/)
explicitly retains NonFreeAssets for artwork, layouts, and prerecorded voices,
NonFreeNet, and a per-build Tracking warning. The GPL label for its code does not
supply permission for every asset. The exact
[metadata snapshot](https://gitlab.com/fdroid/fdroiddata/-/blob/524d813f01d1cdb54e138b1ce8195908a071c52d/metadata/net.osmand.plus.yml)
lists 5.4.11 builds 541101, 541102, and 541103. Their
[build wrapper](https://gitlab.com/f-droid-mirrors/OsmAnd-submodules/-/tree/0bcbf3d414fb47fd574be37b70697121257a952b)
pins the following source graph:

| Component | Exact commit |
| --- | --- |
| Android application | 13934d83aabde68e29dc35ede0575db00e2e5d77 |
| Resources | 7ee9bf7012b48427766afd59c5142b544f9f3214 |
| Native core | a6a8631756afa19601525a625166fef631c6e92d |
| Legacy core | 5a74b81f9c6f6421d9640dccd7cd7a1f3e0061a5 |
| Build support | 12c921624e84acf136e06b11977116e6cfb0283a |
| MPAndroidChart | a235835edb8470229b44c61536608e35f3033a28 |
| Patched ICU mirror | 8e3bd0ea911c6aab8b6aebd69e5208dad18a4016 |

The application commit matches the selected publisher APK's embedded commit.
F-Droid's prebuild script removes Google billing/location/review integrations,
Amazon/Huawei purchase dependencies, Telegram, ANT+, and selected prebuilt
libraries. Its build script rebuilds the core, MPAndroidChart, and patched ICU.
The metadata still declares non-free assets; the scripts do not provide an
asset-license replacement or clearance. This is a useful source-build starting
point, not a cleared redistribution candidate. No F-Droid APK was adopted.

## Exact assets and license boundaries

The [selected commit's LICENSE](https://github.com/osmandapp/OsmAnd/blob/13934d83aabde68e29dc35ede0575db00e2e5d77/LICENSE)
separates GPLv3-or-later code from CC BY-NC-ND 4.0 UI/UX, including layouts and
icons, and warns of proprietary resources. It also describes some transit logos
as fair use. The [resource LICENSE](https://github.com/osmandapp/OsmAnd-resources/blob/7ee9bf7012b48427766afd59c5142b544f9f3214/LICENSE)
refers back to that main license and adds a Flaticon attribution; it does not
supply a clean per-file inventory.

The selected APK's complete cached SHA-256 was reverified. It has 15,765
`assets/` and `res/` entries, totaling 140,009,349 uncompressed bytes. A complete
path/size/SHA-256 inventory remains as an ignored development artifact; its own
hash is recorded in the research evidence. Four concrete bundled resources are:

| APK resource suffix under `assets/OsmAndCore_ResourcesBundle/map/icons/` | Source license description |
| --- | --- |
| `c_subway_chicago.svg.qz` | Chicago Transit Authority logo; fair-use description |
| `c_subway_singapore.svg.qz` | Singapore public transport logo; fair-use description |
| `c_subway_toronto.svg.qz` | TTC logo; fair-use description |
| `c_subway_brussels.svg.qz` | Brussels Metro logo; fair-use description |

After verifying each Qt qCompress length and decoding its zlib payload, all four
SVGs match the corresponding `rendering_styles/style-icons/map-icons-svg/`
files at resource commit 7ee9bf7 byte for byte. Exact paths and hashes are in the
evidence. Those license descriptions do not establish a written emergency-use
grant. Four matching resources also do not establish the complete publisher
APK's resource commit or corresponding-source closure.

The application source contains 3,920 files under `OsmAnd/res/`, including 1,068
layout files and 2,493 drawables. These counts show why replacing a few launcher
icons would not resolve the stated UI/UX scope. They are inventory counts, not
individual copyright determinations.

Voice scope needs precision: the selected APK has 58 JavaScript files under
`assets/voice/` and no prerecorded audio in that directory. The source Gradle
`collectVoiceAssets` task includes only `**/*.js`. Five OGG sounds occur separately
under `assets/sounds/`; their paths are recorded in the evidence. No grant was
inferred for all voice scripts or sounds from the broader voice warning. The
APK also has 14 fonts. A source font-directory Apache-2.0 text is present, but
per-font provenance and complete notices remain unconfirmed.

The publisher's [current legal page](https://osmand.net/docs/legal/license/)
uses CC BY-NC-ND 2.0 for visual elements and describes an application-store
exception for GPL code, while the exact source commit states CC BY-NC-ND 4.0
and scopes its listed store restriction to UI/UX. This research does not resolve
that policy difference or infer a government-distribution exception.

## Source-supported routes remaining

A source build can remove binary-only integrations, as F-Droid demonstrates.
It cannot itself confer redistribution rights on the remaining assets. There
is no verified one-command clean-asset build in the inspected recipe. The
concrete routes are:

1. Obtain documented rights covering the exact unchanged APK and all restricted
   components, then close corresponding source and notices. No request was sent.
2. Prepare a separately pinned source pipeline based on the F-Droid graph, with
   original or independently licensed replacements for the affected UI/layouts,
   icons, sounds, and any other uncleared resources. Keep per-file proof and
   notices. The main license's broad UI/UX scope requires review before treating
   a small artwork substitution as sufficient.

For the second route, the inspected source identifies specific inputs to audit:
`main.res.srcDirs`, `main.assets.srcDirs`, `copyIcons`, `collectVoiceAssets`,
`collectFonts`, the core resource bundle, and the remaining external-resource
copy tasks. It also downloads a miniature world basemap and a star database
from mutable builder URLs. Those inputs would need independent pins and rights
records, or a documented source-generated replacement. The seven top-level
commits above do not close nested native sources, Maven dependencies, or data
inputs.

The F-Droid build's remaining tracking behavior also needs a source and runtime
audit against this project's defaults. Architecture choice, signing, complete
source packaging, repeat builds, and physical offline GPS/map-import tests are
still work to perform after the rights route is established. No APK build was
started, and no candidate catalog records were added for an unqualified build.
