---
{"title": "Краткое руководство", "status": "machine", "reviewer": null, "reviewed_on": null, "review_required": []}
---

## Краткое руководство

Подключите USB-накопитель к телефону или компьютеру. Откройте встроенное приложение «Файлы» или файловый менеджер. Откройте 1_START, затем папку своего языка. Не вставляйте неподходящий разъём силой. [@project_spec]

## Место встречи

{% for rule in defaults.rally_point.rule %}
- {{ rally_labels[rule] }}
{% endfor %}

[@project_spec]

## Время встреч и рация

{{ defaults.meetings.times_local | join(" / ") }} · местное время.

{{ defaults.meetings.if_nobody_there }} [@project_spec]

{{ defaults.radio.service }} · канал {{ defaults.radio.channel }} · {{ defaults.radio.frequency_mhz }} MHz · код приватности: {{ defaults.radio.privacy_code }}.

{{ defaults.radio.listen_window }}. [@project_spec]

## Сообщения соседям

{{ defaults.mesh.app }}. Используйте эти каналы: {{ defaults.mesh.channels.block }} / {{ defaults.mesh.channels.help }}. [@project_spec]

OK означает «в порядке». HELP означает «нужна помощь». [@project_spec]

## Полные руководства

Полные английская и испанская версии находятся в папках ниже. Здесь приведено только краткое руководство.

- English: 1_START/{{ editions.en }}/01_START_phone.pdf
- Español: 1_START/{{ editions.es }}/01_START_phone.pdf

[@project_spec]
