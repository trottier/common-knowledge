---
title: Tarjeta para el refrigerador
status: machine
reviewer: null
reviewed_on: null
source_inputs: {"content/en/card.md": "934813b8319d5b6c77da2124e834d20c5b38a2c21d898fa66961e9e80d3d9a35"}
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

## Mensajes por malla

{{ defaults.mesh.app }}: {{ defaults.mesh.channels.block }} · {{ defaults.mesh.channels.help }}. [@project_spec]

## Escriba aquí

Punto de reunión: ___________________

Contacto del hogar: __________________

Contacto fuera del área: ______________

## Cartel

OK / HELP — BIEN / AYUDA [@project_spec]
