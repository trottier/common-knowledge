---
title: Tarjeta del hogar
status: machine
reviewer: null
reviewed_on: null
source_inputs: {"content/en/card.md": "753fe62e67699ca013d79c12997f0f7e9e1ea6623ff8e341a4be4153389e831b"}
review_required: [radio, legal]
---

## Punto de reunión

{% for rule in defaults.rally_point.rule %}
{{ rally_labels[rule] }}
{% endfor %}
[@project_spec]

## Reúnanse

{{ defaults.meetings.times_local | join(' y ') }}, hora local.
{{ defaults.meetings.if_nobody_there }} [@project_spec]

## Escuche

{{ defaults.radio.service }}, canal {{ defaults.radio.channel }} · {{ defaults.radio.frequency_mhz }} MHz · código de privacidad: {{ defaults.radio.privacy_code }}.
{{ defaults.radio.listen_window }}. [@frs_channels] [@project_spec]

## Abra la reunión

{{ defaults.convener.rule }} [@project_spec]

## Mensajes por malla

{{ defaults.mesh.app }}: {{ defaults.mesh.channels.block }} · {{ defaults.mesh.channels.help }}. [@project_spec]

## Escriba aquí

Punto de reunión: ___________________

Contacto fuera del área: ______________

Medicamentos del hogar: ______________


## Cartel

OK / HELP — BIEN / AYUDA [@project_spec]
