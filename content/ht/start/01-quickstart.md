---
{"title": "Gid pou kòmanse vit", "status": "machine", "reviewer": null, "reviewed_on": null, "review_required": []}
---

## Gid pou kòmanse vit

Konekte kle USB a ak telefòn ou oswa òdinatè a. Louvri aplikasyon Fichye ki deja sou aparèy la. Louvri 1_START, apre sa katab lang ou a. Pa fòse yon konektè ki pa antre. [@project_spec]

## Kote pou rasanble

{% for rule in defaults.rally_point.rule %}
- {{ rally_labels[rule] }}
{% endfor %}

[@project_spec]

## Lè reyinyon ak radyo

{{ defaults.meetings.times_local | join(" / ") }} · lè lokal.

{{ defaults.meetings.if_nobody_there }} [@project_spec]

{{ defaults.radio.service }} · chanèl {{ defaults.radio.channel }} · {{ defaults.radio.frequency_mhz }} MHz · kòd vi prive: {{ defaults.radio.privacy_code }}.

{{ defaults.radio.listen_window }}. [@project_spec]

## Mesaj pou vwazen

{{ defaults.mesh.app }}. Sèvi ak chanèl sa yo: {{ defaults.mesh.channels.block }} / {{ defaults.mesh.channels.help }}. [@project_spec]

OK vle di anfòm. HELP vle di bezwen èd. [@project_spec]

## Gid konplè

Gid konplè an anglè ak panyòl yo nan katab ki anba yo. Vèsyon sa a se yon gid rapid sèlman.

- English: 1_START/{{ editions.en }}/01_START_phone.pdf
- Español: 1_START/{{ editions.es }}/01_START_phone.pdf

[@project_spec]
