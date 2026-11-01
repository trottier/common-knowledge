# Android map reproducibility

A real Guam repeat from the same filtered input produced two OBFs of the same
length with 1,582 different bytes. Both had valid map, routing and POI indexes
and the fixed creation date. The filtered OSM source, source notice and all other
bound metadata matched. The national controller stopped rather than pinning a
successful repeat.

The [publisher's POI generator source](https://github.com/osmandapp/OsmAnd-tools/blob/b601887fc5603bd65f7eafc9d7d32c42c572a342/java-tools/OsmAndMapCreatorUtilities/src/main/java/net/osmand/obf/preparation/IndexPoiCreator.java)
uses object-keyed hash collections for additional POI attributes; the inspected
`PoiAdditionalType` class inherits object identity hashing. This is consistent
with the observed ordering changes. The exact nightly converter archive remains
pinned separately; its license-proof commit is not asserted to identify every
byte of the nightly binary.

The [pinned JDK 17.0.21 source](https://github.com/openjdk/jdk17u/blob/jdk-17.0.21%2B9/src/hotspot/share/runtime/synchronizer.cpp)
defines HotSpot identity-hash mode 2 as a constant hash. Three separate diagnostic
Guam conversions with that VM mode produced identical OBFs and complete
manifests. They were research outputs, not silently adopted as production pins.

The production converter now reads `jvm_identity_hash` from
`pipelines/androidmaps/settings.yaml`, requires mode 2, and passes HotSpot's
experimental-option unlock plus that mode to the original Java tool. The exact
JVM options are recorded with tool versions in the generation manifest. The
publisher JARs and source databases are not modified. Both conversion and
inspection fail if the pinned runtime rejects the options.

This setting is specific to the pinned HotSpot runtime, whose own flag is
labelled unstable. It can increase object-hash collisions, so larger-state
conversion performance and repeat results still need measurement. It does not
prove deterministic insertion order in every converter path, clear app asset
rights, certify routes or replace physical import/GPS testing. Fresh production
Guam repeats and the remaining national maps are still being validated.
