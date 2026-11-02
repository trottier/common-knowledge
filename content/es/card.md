---
title: Tarjeta del hogar
status: machine
reviewer: null
reviewed_on: null
source_inputs: {"content/en/card.md": "a34b2fab3f7d2b4efe19326aea66874d38eed1b0d5fcd2c458e3a7f8b04d08e5"}
review_required: [radio, legal]
---


{{ defaults.plan_is_fixed }} [@project_spec]

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
