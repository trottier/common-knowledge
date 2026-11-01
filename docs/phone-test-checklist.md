# Manual phone and laptop checks

No physical device checks have been completed. Record tester, device model,
operating system, adapter, drive part, source commit, variant, profile, and result for every row.
A passing automated PDF test is not a physical phone test.

Devices: USB-C iPhone; Lightning iPhone with adapter; recent Pixel; budget Samsung;
budget Motorola; Windows, Mac, and Linux laptops. Include one laptop with only
USB-A ports, using a USB-C to USB-A adapter. The drive itself has only USB-C.

- [ ] Drive mounts; phone PDFs open without an app install.
- [ ] Contents links and bookmarks work; text is readable without zooming.
- [ ] iPhone Compass coordinates locate a position on an atlas grid.
- [ ] Find a map through the actual state/county folders and complete area/ZIP filenames;
      use the overview, places index, and continuation references without a website.
- [ ] Record cold-open and zoom/pan behavior, repeated page switching, PDF bytes, viewer,
      and memory limitations on older and low-memory phones. Desktop presets do not
      establish physical-phone results or the configured coverage target.
- [ ] Android OsmAnd installs from the drive, imports a state and shows offline GPS.
- [ ] Kiwix opens WikEM on Android and laptops; medical PDFs open on iPhone.
- [ ] Laptop map opens from the USB HTML file, reads its chosen map, and pans/zooms offline.
- [ ] bitchat connects two Android phones without networking; Briar shares itself offline.
- [ ] Video plays in English by default on every device.
- [ ] iPhone player switches to Spanish audio and subtitles where supplied.
- [ ] VLC on Android switches video audio and subtitle languages.
- [ ] Phone pack copies locally and shares to another phone with AirDrop or Quick Share.
- [ ] BACKUP copies open and match the primary core documents.

Before release, complete the checklist on at least three phones and two laptop
operating systems, as required by the specification. Do not mark a row complete
from emulator or container results.

## Offline AI: v0.2 only

These checks apply when offline AI is integrated on variants 7 and 8. They are
not requirements for v0.1 or the current Variant 1/Rhode Island sample.

- [ ] Offline AI starts on each laptop OS and answers in English and Spanish.
- [ ] Android offline AI loads the model on a phone with at least 6 GB RAM.
