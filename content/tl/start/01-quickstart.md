---
{"title": "Mabilis na panimula", "status": "machine", "reviewer": null, "reviewed_on": null, "review_required": []}
---

## Mabilis na panimula

Ikabit ang USB sa telepono o computer. Buksan ang built-in na Files app o file manager. Buksan ang 1_START, saka ang folder ng iyong wika. Huwag piliting ikabit ang konektor na hindi kasya. [@project_spec]

## Tagpuan

{% for rule in defaults.rally_point.rule %}
- {{ rally_labels[rule] }}
{% endfor %}

[@project_spec]

## Oras ng pagtitipon at radyo

{{ defaults.meetings.times_local | join(" / ") }} · lokal na oras.

{{ defaults.meetings.if_nobody_there }} [@project_spec]

{{ defaults.radio.service }} · channel {{ defaults.radio.channel }} · {{ defaults.radio.frequency_mhz }} MHz · privacy code: {{ defaults.radio.privacy_code }}.

{{ defaults.radio.listen_window }}. [@project_spec]

## Mensahe sa mga kapitbahay

{{ defaults.mesh.app }}. Gamitin ang mga channel na ito: {{ defaults.mesh.channels.block }} / {{ defaults.mesh.channels.help }}. [@project_spec]

Ang OK ay maayos. Ang HELP ay humihingi ng tulong. [@project_spec]

## Buong gabay

Nasa mga folder sa ibaba ang buong gabay sa Ingles at Espanyol. Mabilis na panimula lamang ang bersiyong ito.

- English: 1_START/{{ editions.en }}/01_START_phone.pdf
- Español: 1_START/{{ editions.es }}/01_START_phone.pdf

[@project_spec]
