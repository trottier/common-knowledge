---
{"title": "راهنمای شروع سریع", "status": "machine", "reviewer": null, "reviewed_on": null, "review_required": []}
---

## راهنمای شروع سریع

حافظهٔ USB را به تلفن یا رایانه وصل کنید. برنامهٔ داخلی فایل‌ها یا مدیر فایل را باز کنید. وارد 1_START و سپس پوشهٔ زبان خود شوید. رابطی را که اندازه نیست با فشار وارد نکنید. [@project_spec]

## محل گردهمایی

{% for rule in defaults.rally_point.rule %}
- {{ rally_labels[rule] }}
{% endfor %}

[@project_spec]

## زمان دیدار و بی‌سیم

{{ defaults.meetings.times_local | join(" / ") }} · به وقت محلی.

{{ defaults.meetings.if_nobody_there }} [@project_spec]

{{ defaults.radio.service }} · کانال {{ defaults.radio.channel }} · {{ defaults.radio.frequency_mhz }} MHz · کد حریم خصوصی: {{ defaults.radio.privacy_code }}.

{{ defaults.radio.listen_window }}. [@project_spec]

## پیام‌های همسایه‌ها

{{ defaults.mesh.app }}. از این کانال‌ها استفاده کنید: {{ defaults.mesh.channels.block }} / {{ defaults.mesh.channels.help }}. [@project_spec]

OK یعنی خوب هستم. HELP یعنی به کمک نیاز دارم. [@project_spec]

## راهنماهای کامل

راهنماهای کامل انگلیسی و اسپانیایی در پوشه‌های زیر هستند. این نسخه فقط راهنمای شروع سریع است.

- English: 1_START/{{ editions.en }}/01_START_phone.pdf
- Español: 1_START/{{ editions.es }}/01_START_phone.pdf

[@project_spec]
