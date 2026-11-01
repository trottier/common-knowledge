# OsmAnd release provenance and distribution hold

The official release index supplies `net.osmand-5.4.11-5411.apk`, 389,255,401
bytes. The complete HTTPS download passes ZIP CRC and `apksigner verify` checks.
Its SHA-256 is pinned in `catalog/apk.yaml`; the publisher does not supply that
SHA-256 in the directory listing, so human pin review remains required.

The verified certificate SHA-256 matches `net.osmand` in the publisher's
[Android asset links](https://osmand.net/.well-known/assetlinks.json).
The APK's `META-INF/version-control-info.textproto` names commit
`13934d83aabde68e29dc35ede0575db00e2e5d77`. The catalog pins the corresponding
GitHub source archive by exact commit, measured size and computed SHA-256.
The archive's LICENSE bytes match the file fetched from that exact commit.
These checks establish provenance; they do not establish complete corresponding
source or permission to distribute the combined release.

The [license at that commit](https://github.com/osmandapp/OsmAnd/blob/13934d83aabde68e29dc35ede0575db00e2e5d77/LICENSE)
distinguishes GPLv3-or-later code from CC BY-NC-ND 4.0 artwork, proprietary
artwork and voice files, and other third-party resources. It also lists some
metro icons under fair-use descriptions. Which resources occur in this exact
APK, their notices and their emergency-drive redistribution rights require
review. The complete application must not be labeled solely GPL.

Both application and source candidate remain blocked by explicit license
markers and named legal-review gates. Restricted material also requires written
permission. No permission has been requested or granted by this provenance work.
The assembler and release packager must keep rejecting these entries until the
required rights and source closure are established.

The generated roads-and-places map data has its own OpenStreetMap/ODbL
provenance. Map-generation work can continue while application distribution is
unresolved. Phone-tested installation and map-import instructions remain open.

Publisher evidence:

- [Official release index](https://download.osmand.net/releases/)
- [Exact application source commit](https://github.com/osmandapp/OsmAnd/commit/13934d83aabde68e29dc35ede0575db00e2e5d77)
- [Exact source archive](https://codeload.github.com/osmandapp/OsmAnd/tar.gz/13934d83aabde68e29dc35ede0575db00e2e5d77)

The follow-up [redistribution research](osmand-redistribution-research.md) pins
F-Droid's source graph, identifies four actual transit-logo assets in this APK,
and records the remaining clean-build routes. It does not clear a replacement.
