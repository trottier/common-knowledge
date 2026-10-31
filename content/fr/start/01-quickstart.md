---
{"title": "Guide de démarrage rapide", "status": "machine", "reviewer": null, "reviewed_on": null, "review_required": []}
---

## Guide de démarrage rapide

Branchez la clé USB au téléphone ou à l’ordinateur. Ouvrez l’application Fichiers intégrée ou le gestionnaire de fichiers. Ouvrez 1_START, puis le dossier de votre langue. Ne forcez pas un connecteur qui ne convient pas. [@project_spec]

## Point de rendez-vous

{% for rule in defaults.rally_point.rule %}
- {{ rally_labels[rule] }}
{% endfor %}

[@project_spec]

## Horaires et radio

{{ defaults.meetings.times_local | join(" / ") }} · heure locale.

{{ defaults.meetings.if_nobody_there }} [@project_spec]

{{ defaults.radio.service }} · canal {{ defaults.radio.channel }} · {{ defaults.radio.frequency_mhz }} MHz · code de confidentialité: {{ defaults.radio.privacy_code }}.

{{ defaults.radio.listen_window }}. [@project_spec]

## Messages aux voisins

{{ defaults.mesh.app }}. Utilisez ces canaux: {{ defaults.mesh.channels.block }} / {{ defaults.mesh.channels.help }}. [@project_spec]

OK signifie que ça va. HELP signifie besoin d’aide. [@project_spec]

## Guides complets

Les guides complets en anglais et en espagnol sont dans les dossiers ci-dessous. Cette édition est seulement un guide rapide.

- English: 1_START/{{ editions.en }}/01_START_phone.pdf
- Español: 1_START/{{ editions.es }}/01_START_phone.pdf

[@project_spec]
