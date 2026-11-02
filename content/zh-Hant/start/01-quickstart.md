---
{"title": "快速入門", "status": "machine", "reviewer": null, "reviewed_on": null, "review_required": []}
---


{{ defaults.plan_is_fixed }} [@project_spec]

## 快速入門

將此隨身碟連接到手機或電腦。開啟手機內建的「檔案」應用程式或電腦的檔案管理員。開啟 1_START，再開啟您的語言資料夾。不要強插不相容的接頭。 [@project_spec]

## 集合地點

{% for rule in defaults.rally_point.rule %}
- {{ rally_labels[rule] }}
{% endfor %}

[@project_spec]

## 集合時間與無線電

{{ defaults.meetings.times_local | join(" / ") }} · 當地時間.

{{ defaults.meetings.if_nobody_there }} [@project_spec]

{{ defaults.radio.service }} · 頻道 {{ defaults.radio.channel }} · {{ defaults.radio.frequency_mhz }} MHz · 靜音碼: {{ defaults.radio.privacy_code }}.

{{ defaults.radio.listen_window }}. [@project_spec]

## 鄰里訊息

{{ defaults.mesh.app }}. 使用以下頻道: {{ defaults.mesh.channels.block }} / {{ defaults.mesh.channels.help }}. [@project_spec]

OK 表示「好」。HELP 表示「求助」。 [@project_spec]

## 完整指南

完整的英語和西班牙語指南位於下列資料夾。此版本只有快速入門。

- English: 1_START/{{ editions.en }}/01_START_phone.pdf
- Español: 1_START/{{ editions.es }}/01_START_phone.pdf

[@project_spec]
