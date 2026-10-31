---
{"title": "빠른 시작 안내", "status": "machine", "reviewer": null, "reviewed_on": null, "review_required": []}
---

## 빠른 시작 안내

USB 드라이브를 휴대전화나 컴퓨터에 연결하세요. 기본 파일 앱이나 파일 관리자를 여세요. 1_START를 열고 사용 언어 폴더를 여세요. 맞지 않는 연결 단자를 억지로 끼우지 마세요. [@project_spec]

## 모임 장소

{% for rule in defaults.rally_point.rule %}
- {{ rally_labels[rule] }}
{% endfor %}

[@project_spec]

## 모임 시간과 무전기

{{ defaults.meetings.times_local | join(" / ") }} · 현지 시간.

{{ defaults.meetings.if_nobody_there }} [@project_spec]

{{ defaults.radio.service }} · 채널 {{ defaults.radio.channel }} · {{ defaults.radio.frequency_mhz }} MHz · 프라이버시 코드: {{ defaults.radio.privacy_code }}.

{{ defaults.radio.listen_window }}. [@project_spec]

## 이웃 메시지

{{ defaults.mesh.app }}. 다음 채널을 사용하세요: {{ defaults.mesh.channels.block }} / {{ defaults.mesh.channels.help }}. [@project_spec]

OK는 괜찮다는 뜻입니다. HELP는 도움이 필요하다는 뜻입니다. [@project_spec]

## 전체 안내

영어와 스페인어 전체 안내는 아래 폴더에 있습니다. 이 언어판에는 빠른 시작 안내만 있습니다.

- English: 1_START/{{ editions.en }}/01_START_phone.pdf
- Español: 1_START/{{ editions.es }}/01_START_phone.pdf

[@project_spec]
