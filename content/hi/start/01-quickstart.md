---
{"title": "जल्दी शुरू करने की मार्गदर्शिका", "status": "machine", "reviewer": null, "reviewed_on": null, "review_required": []}
---


{{ defaults.plan_is_fixed }} [@project_spec]

## जल्दी शुरू करने की मार्गदर्शिका

USB ड्राइव को फ़ोन या कंप्यूटर से जोड़ें। पहले से मौजूद फ़ाइल ऐप या फ़ाइल मैनेजर खोलें। 1_START खोलें और अपनी भाषा का फ़ोल्डर चुनें। जो कनेक्टर सही न बैठे, उसे ज़ोर से न लगाएँ। [@project_spec]

## मिलने की जगह

{% for rule in defaults.rally_point.rule %}
- {{ rally_labels[rule] }}
{% endfor %}

[@project_spec]

## बैठक का समय और रेडियो

{{ defaults.meetings.times_local | join(" / ") }} · स्थानीय समय.

{{ defaults.meetings.if_nobody_there }} [@project_spec]

{{ defaults.radio.service }} · चैनल {{ defaults.radio.channel }} · {{ defaults.radio.frequency_mhz }} MHz · प्राइवेसी कोड: {{ defaults.radio.privacy_code }}.

{{ defaults.radio.listen_window }}. [@project_spec]

## पड़ोसियों के संदेश

{{ defaults.mesh.app }}. इन चैनलों का उपयोग करें: {{ defaults.mesh.channels.block }} / {{ defaults.mesh.channels.help }}. [@project_spec]

OK का मतलब ठीक है। HELP का मतलब मदद चाहिए। [@project_spec]

## पूरी मार्गदर्शिकाएँ

अंग्रेज़ी और स्पेनिश में पूरी मार्गदर्शिकाएँ नीचे दिए फ़ोल्डरों में हैं। यह संस्करण केवल एक छोटी शुरुआती मार्गदर्शिका है।

- English: 1_START/{{ editions.en }}/01_START_phone.pdf
- Español: 1_START/{{ editions.es }}/01_START_phone.pdf

[@project_spec]
