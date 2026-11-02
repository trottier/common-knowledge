---
title: Comunicaciones
status: machine
reviewer: null
reviewed_on: null
source_inputs: {"content/en/start/07-comms.md": "9b3e2f16311e4730a4d9e159196efc7ce44492c0b45abfae8abe08b4c778ed7c"}
review_required: [radio, legal]
---


{{ defaults.plan_is_fixed }} [@project_spec]

## Detecte mensajes falsos

Los avisos oficiales pueden llegar por Wireless Emergency Alerts, NOAA Weather Radio y emisiones de radio o televisión. [@fema_alert_channels]
Un mensaje en el chat de malla no es un aviso oficial verificado. [@project_spec]
Confirme en persona, en la próxima reunión, un mensaje que le envíe a un lugar nuevo. [@project_spec]
No espere a la reunión si corre peligro inmediato; póngase a salvo. [@project_spec]
[[VERIFY: revisión por especialistas en emergencias de las instrucciones sobre avisos urgentes, evacuación y confirmación en persona.]]

No instale nada ni pague solo porque lo diga un mensaje. [@fbi_verify_contacts]
Una voz conocida puede ser copiada. [@ftc_voice_scams]
Si el servicio funciona, vuelva a llamar a un número que ya conozca. [@ftc_voice_scams]
Acuerde una palabra clave familiar privada cuando puedan reunirse. [@fbi_verify_contacts]
No la comparta en un canal público ni la considere una garantía. [@project_spec]
No hace falta una palabra clave ni preparación previa para usar esta unidad. [@project_spec]

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
