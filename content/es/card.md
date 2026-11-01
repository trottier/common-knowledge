---
title: Tarjeta del hogar
status: machine
reviewer: null
reviewed_on: null
source_inputs: {"content/en/card.md": "dee068cb80e1e272983d6e28c2aa39f5ba32c6265e317f6471b9bdb5d777819f"}
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

{% if not variants.offline_ai_enabled %}
IA sin conexión aplazada. Unidades futuras: {{ variants.offline_ai | join(' y ') }}. [@project_spec]
{% endif %}

## Cartel

OK / HELP — BIEN / AYUDA [@project_spec]
