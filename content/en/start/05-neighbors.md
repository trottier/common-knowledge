---
title: Meeting your neighbors
status: draft
reviewer: null
reviewed_on: null
review_required: []
---

## Find the rally point

Follow the first rule that applies, in this order: [@project_spec]

{% for rule in defaults.rally_point.rule %}
- {{ rally_labels[rule] }}
{% endfor %}

Do not enter a school, station or place of worship without permission.
[[VERIFY: approve national guidance for an unsafe, closed or inaccessible entrance.]]

## Meet at the same times

{{ defaults.meetings.times_local | join(' and ') }} local time.
{{ defaults.meetings.if_nobody_there }} [@project_spec]

## Pick the convener

{{ defaults.convener.rule }}
{{ defaults.convener.rotation }}
{{ defaults.convener.role_fallback }} [@project_spec]

## The 15-minute meeting script

Read this proposed script aloud. [@project_spec]

1. “Who needs urgent help? Who is missing?”
2. “What hazards do we know about? Say what you saw and when.”
3. “Who can check on people who need support? Ask before entering homes.”
4. “What can we share? Who can help with water, food and safe power?”
5. “Choose one person for each task. Repeat the task and next check-in.”
6. “Who will convene the next meeting? Read the meeting times again.”

Do not post private health details or name a shelter as open without confirmation.
[[VERIFY: field-test timing, consent, accessibility and the proposed meeting script.]]
