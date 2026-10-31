---
{"title": "Hướng dẫn bắt đầu nhanh", "status": "machine", "reviewer": null, "reviewed_on": null, "review_required": []}
---

## Hướng dẫn bắt đầu nhanh

Cắm ổ USB vào điện thoại hoặc máy tính. Mở ứng dụng Tệp có sẵn hoặc trình quản lý tệp. Mở 1_START, rồi mở thư mục ngôn ngữ của bạn. Không cố cắm đầu nối không vừa. [@project_spec]

## Điểm tập trung

{% for rule in defaults.rally_point.rule %}
- {{ rally_labels[rule] }}
{% endfor %}

[@project_spec]

## Giờ họp và bộ đàm

{{ defaults.meetings.times_local | join(" / ") }} · giờ địa phương.

{{ defaults.meetings.if_nobody_there }} [@project_spec]

{{ defaults.radio.service }} · kênh {{ defaults.radio.channel }} · {{ defaults.radio.frequency_mhz }} MHz · mã riêng tư: {{ defaults.radio.privacy_code }}.

{{ defaults.radio.listen_window }}. [@project_spec]

## Tin nhắn hàng xóm

{{ defaults.mesh.app }}. Dùng các kênh sau: {{ defaults.mesh.channels.block }} / {{ defaults.mesh.channels.help }}. [@project_spec]

OK nghĩa là ổn. HELP nghĩa là cần giúp đỡ. [@project_spec]

## Hướng dẫn đầy đủ

Bản tiếng Anh và tiếng Tây Ban Nha đầy đủ ở các thư mục dưới đây. Bản này chỉ là hướng dẫn nhanh.

- English: 1_START/{{ editions.en }}/01_START_phone.pdf
- Español: 1_START/{{ editions.es }}/01_START_phone.pdf

[@project_spec]
