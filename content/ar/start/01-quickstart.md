---
{"title": "دليل البدء السريع", "status": "machine", "reviewer": null, "reviewed_on": null, "review_required": []}
---


{{ defaults.plan_is_fixed }} [@project_spec]

## دليل البدء السريع

صل وحدة USB بالهاتف أو الكمبيوتر. افتح تطبيق الملفات المدمج أو مدير الملفات. افتح 1_START ثم مجلد لغتك. لا تجبر موصلاً لا يلائم المنفذ. [@project_spec]

## نقطة التجمع

{% for rule in defaults.rally_point.rule %}
- {{ rally_labels[rule] }}
{% endfor %}

[@project_spec]

## مواعيد اللقاء والراديو

{{ defaults.meetings.times_local | join(" / ") }} · بالتوقيت المحلي.

{{ defaults.meetings.if_nobody_there }} [@project_spec]

{{ defaults.radio.service }} · القناة {{ defaults.radio.channel }} · {{ defaults.radio.frequency_mhz }} MHz · رمز الخصوصية: {{ defaults.radio.privacy_code }}.

{{ defaults.radio.listen_window }}. [@project_spec]

## رسائل الجيران

{{ defaults.mesh.app }}. استخدم القنوات التالية: {{ defaults.mesh.channels.block }} / {{ defaults.mesh.channels.help }}. [@project_spec]

تعني OK بخير. وتعني HELP أحتاج إلى مساعدة. [@project_spec]

## الدليل الكامل

توجد النسختان الكاملتان بالإنجليزية والإسبانية في المجلدين التاليين. هذه النسخة دليل سريع فقط.

- English: 1_START/{{ editions.en }}/01_START_phone.pdf
- Español: 1_START/{{ editions.es }}/01_START_phone.pdf

[@project_spec]
