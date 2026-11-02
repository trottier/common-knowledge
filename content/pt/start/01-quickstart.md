---
{"title": "Guia rápido", "status": "machine", "reviewer": null, "reviewed_on": null, "review_required": []}
---


{{ defaults.plan_is_fixed }} [@project_spec]

## Guia rápido

Conecte a unidade USB ao telefone ou computador. Abra o aplicativo de arquivos integrado ou o gerenciador de arquivos. Abra 1_START e a pasta do seu idioma. Não force um conector que não encaixa. [@project_spec]

## Ponto de encontro

{% for rule in defaults.rally_point.rule %}
- {{ rally_labels[rule] }}
{% endfor %}

[@project_spec]

## Horários e rádio

{{ defaults.meetings.times_local | join(" / ") }} · hora local.

{{ defaults.meetings.if_nobody_there }} [@project_spec]

{{ defaults.radio.service }} · canal {{ defaults.radio.channel }} · {{ defaults.radio.frequency_mhz }} MHz · código de privacidade: {{ defaults.radio.privacy_code }}.

{{ defaults.radio.listen_window }}. [@project_spec]

## Mensagens aos vizinhos

{{ defaults.mesh.app }}. Use estes canais: {{ defaults.mesh.channels.block }} / {{ defaults.mesh.channels.help }}. [@project_spec]

OK significa bem. HELP significa preciso de ajuda. [@project_spec]

## Guias completos

Os guias completos em inglês e espanhol estão nas pastas abaixo. Esta edição contém apenas um guia rápido.

- English: 1_START/{{ editions.en }}/01_START_phone.pdf
- Español: 1_START/{{ editions.es }}/01_START_phone.pdf

[@project_spec]
