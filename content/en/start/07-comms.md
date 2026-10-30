---
title: Communications
status: draft
reviewer: null
reviewed_on: null
review_required: [radio, legal]
---

## Radio

Use a certified {{ defaults.radio.service }} radio on channel {{ defaults.radio.channel }}.
The frequency is {{ defaults.radio.frequency_mhz }} MHz.
Privacy code: {{ defaults.radio.privacy_code }}. [@frs_channels]

Listen: {{ defaults.radio.listen_window }}. [@project_spec]
[[VERIFY: radio reviewer must confirm licensing, equipment certification, channel selection and how to turn off privacy codes.]]

## Mesh messages

The shared app is {{ defaults.mesh.app }}.
Block channel: {{ defaults.mesh.channels.block }}.
Help channel: {{ defaults.mesh.channels.help }}.
{{ defaults.mesh.schedule }} [@project_spec]

Use these message formats:

- {{ defaults.mesh.formats.help }}
- {{ defaults.mesh.formats.ok }} [@project_spec]

Do not send private medical details to a public channel.
[[VERIFY: test these exact channels and formats in the pinned Android APK with no internet. Bluetooth and location permissions may be needed; write the tested flow.]]

## Calls, texts and weather

For an emergency, call 911 if you can. Text if you cannot call. [@calling_911]
Use short texts for routine family check-ins to limit network load. [@fcc_disaster]
Use a NOAA Weather Radio receiver for weather broadcasts. [@noaa_radio]
Do not assume an ordinary AM/FM radio receives the weather band. [@noaa_radio]

## Satellite SOS

Some iPhones offer Emergency SOS through a satellite when cellular and Wi-Fi service are unavailable.
Follow the phone's on-screen directions if it offers the feature. [@apple_satellite]
Do not assume every phone, location or account supports it. [@apple_satellite]
[[VERIFY: test current supported iPhone and Android satellite SOS flows and limitations without requiring advance setup.]]
