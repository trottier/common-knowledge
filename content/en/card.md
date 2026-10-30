---
title: Fridge card
status: draft
reviewer: null
reviewed_on: null
review_required: [radio, legal]
---

## Rally point

{% for rule in defaults.rally_point.rule %}
{% if rule == 'written_on_card' %}
Use the place written on this card.
{% elif rule == 'nearest_public_elementary_school_main_entrance' %}
Otherwise use the nearest public elementary school's main entrance.
{% elif rule == 'nearest_fire_station' %}
If no school is within walking distance, use the nearest fire station.
{% elif rule == 'nearest_place_of_worship' %}
If neither is available, use the nearest place of worship.
{% endif %}
{% endfor %}
[@project_spec]

## Meet

{{ defaults.meetings.times_local | join(' and ') }} local time.
{{ defaults.meetings.if_nobody_there }} [@project_spec]

## Listen

{{ defaults.radio.service }} channel {{ defaults.radio.channel }} · {{ defaults.radio.frequency_mhz }} MHz · privacy code {{ defaults.radio.privacy_code }}.
{{ defaults.radio.listen_window }}. [@frs_channels] [@project_spec]

## Mesh

{{ defaults.mesh.app }}: {{ defaults.mesh.channels.block }} · {{ defaults.mesh.channels.help }}. [@project_spec]

## Write in

Rally point: ________________________

Household contact: __________________

Out-of-area contact: _________________

## Placard

OK / HELP [@project_spec]
