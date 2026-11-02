---
title: Maps and places
status: draft
reviewer: null
reviewed_on: null
review_required: []
---

## Find your coordinates

On iPhone, open Compass to see your current location when available. [@apple_compass]
[[VERIFY: test degrees-minutes-seconds display and location-permission prompts on current iPhones.]]

Find your state and county in `3_MAPS_AND_PLACES`.
Match the latitude and longitude to the grid labels.
Use the directory's page and grid square to find a listed place. [@project_spec]

Do not treat a directory entry as a promise that the place is open.
Each page says “may help; not confirmed open.” [@project_spec]

## If GPS is wrong or unavailable

GPS signals can be blocked or faked. [@gps_interference]
Cross-check the phone's position with street signs and the places index. [@project_spec]
If they disagree, stop relying on the phone's position and check the signs. [@project_spec]
Use the compass built into the drive to orient the map. [@project_spec]
Do not follow a location dot into a dangerous or closed route. [@project_spec]
[[VERIFY: field-test paper/PDF map orientation with the drive compass, true/grid/magnetic north, and safe conflicting-sign/GPS guidance.]]

## Android map

The optional Android map app and import guide are in `3_MAPS_AND_PLACES/android`. [@project_spec]
[[VERIFY: insert the phone-tested OsmAnd installation and state-map import flow.]]

## Laptop map

The laptop map is on the variant whose in-depth knowledge collection lists it.
Use **How is my drive different?** to find that variant. [@project_spec]
[[VERIFY: test the pinned offline map viewer launcher on each laptop operating system.]]
