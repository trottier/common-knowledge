---
{"title": "Skrócona instrukcja", "status": "machine", "reviewer": null, "reviewed_on": null, "review_required": []}
---


{{ defaults.plan_is_fixed }} [@project_spec]

## Skrócona instrukcja

Podłącz pamięć USB do telefonu lub komputera. Otwórz wbudowaną aplikację Pliki lub menedżer plików. Otwórz 1_START i folder swojego języka. Nie wciskaj na siłę niepasującego złącza. [@project_spec]

## Miejsce spotkania

{% for rule in defaults.rally_point.rule %}
- {{ rally_labels[rule] }}
{% endfor %}

[@project_spec]

## Godziny spotkań i radio

{{ defaults.meetings.times_local | join(" / ") }} · czas lokalny.

{{ defaults.meetings.if_nobody_there }} [@project_spec]

{{ defaults.radio.service }} · kanał {{ defaults.radio.channel }} · {{ defaults.radio.frequency_mhz }} MHz · kod prywatności: {{ defaults.radio.privacy_code }}.

{{ defaults.radio.listen_window }}. [@project_spec]

## Wiadomości do sąsiadów

{{ defaults.mesh.app }}. Użyj tych kanałów: {{ defaults.mesh.channels.block }} / {{ defaults.mesh.channels.help }}. [@project_spec]

OK oznacza „w porządku”. HELP oznacza „potrzebna pomoc”. [@project_spec]

## Pełne instrukcje

Pełne instrukcje po angielsku i hiszpańsku są w poniższych folderach. Ta wersja zawiera tylko skróconą instrukcję.

- English: 1_START/{{ editions.en }}/01_START_phone.pdf
- Español: 1_START/{{ editions.es }}/01_START_phone.pdf

[@project_spec]
