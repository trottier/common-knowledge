---
title: Comunicaciones
status: machine
reviewer: null
reviewed_on: null
source_inputs: {"content/en/start/07-comms.md": "c764aa1a61fd6e3b180685154b6f02fde9cc73789cd791a8c505027e3634a4fb"}
review_required: [radio, legal]
---

## Radio

Use una radio {{ defaults.radio.service }} certificada en el canal {{ defaults.radio.channel }}.
La frecuencia es {{ defaults.radio.frequency_mhz }} MHz.
Código de privacidad: {{ defaults.radio.privacy_code }}. [@frs_channels]

Escuche durante: {{ defaults.radio.listen_window }}. [@project_spec]
[[VERIFY: revisión de licencias, certificación del equipo, selección del canal y desactivación de los códigos de privacidad.]]

## Mensajes por malla

La aplicación compartida es {{ defaults.mesh.app }}.
Canal del barrio: {{ defaults.mesh.channels.block }}.
Canal de ayuda: {{ defaults.mesh.channels.help }}.
{{ defaults.mesh.schedule }} [@project_spec]

Use estos formatos:

- {{ defaults.mesh.formats.help }}
- {{ defaults.mesh.formats.ok }} [@project_spec]

En esos formatos, sustituya `address` por la dirección y `need` por la necesidad.
No envíe datos médicos privados a un canal público.
[[VERIFY: probar estos canales y formatos exactos en el APK fijado, sin internet; documentar permisos y pasos comprobados.]]

## Llamadas, textos y tiempo meteorológico

Ante una emergencia, llame al 911 si puede. Envíe un texto si no puede llamar. [@calling_911]
Use textos cortos para contactos familiares que no sean urgentes, para reducir la carga de la red. [@fcc_disaster]
Use un receptor NOAA Weather Radio para escuchar los avisos meteorológicos. [@noaa_radio]
No suponga que una radio AM/FM común recibe esa banda. [@noaa_radio]

## SOS por satélite

Algunos iPhone permiten pedir ayuda de emergencia por satélite cuando no hay servicio celular ni Wi-Fi.
Siga las instrucciones en pantalla si el teléfono ofrece esa función. [@apple_satellite]
No suponga que todos los teléfonos, lugares o cuentas la admiten. [@apple_satellite]
[[VERIFY: probar los pasos y límites actuales del SOS por satélite en iPhone y Android sin exigir preparación previa.]]
