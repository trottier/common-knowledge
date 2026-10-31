---
{"title": "快速入门", "status": "machine", "reviewer": null, "reviewed_on": null, "review_required": []}
---

## 快速入门

将此盘连接到手机或电脑。打开手机自带的“文件”应用或电脑的文件管理器。打开 1_START，再打开您的语言文件夹。不要强插不匹配的接口。 [@project_spec]

## 集合地点

{% for rule in defaults.rally_point.rule %}
- {{ rally_labels[rule] }}
{% endfor %}

[@project_spec]

## 集合时间和无线电

{{ defaults.meetings.times_local | join(" / ") }} · 当地时间.

{{ defaults.meetings.if_nobody_there }} [@project_spec]

{{ defaults.radio.service }} · 频道 {{ defaults.radio.channel }} · {{ defaults.radio.frequency_mhz }} MHz · 静音码: {{ defaults.radio.privacy_code }}.

{{ defaults.radio.listen_window }}. [@project_spec]

## 邻里消息

{{ defaults.mesh.app }}. 使用以下频道: {{ defaults.mesh.channels.block }} / {{ defaults.mesh.channels.help }}. [@project_spec]

OK 表示“好”。HELP 表示“求助”。 [@project_spec]

## 完整指南

完整的英语和西班牙语指南在下列文件夹中。此版本只有快速入门。

- English: 1_START/{{ editions.en }}/01_START_phone.pdf
- Español: 1_START/{{ editions.es }}/01_START_phone.pdf

[@project_spec]
