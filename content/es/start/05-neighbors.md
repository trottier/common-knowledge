---
title: Reunirse con los vecinos
status: machine
reviewer: null
reviewed_on: null
source_inputs: {"content/en/start/05-neighbors.md": "b91583a7b0f22c4c7bdfd310835fadb589a08192a6b5c19ee15c3dcdec2a939c"}
review_required: []
---


{{ defaults.plan_is_fixed }} [@project_spec]

## Encuentre el punto de reunión

Siga la primera regla que corresponda, en este orden: [@project_spec]

{% for rule in defaults.rally_point.rule %}
- {{ rally_labels[rule] }}
{% endfor %}

No entre en una escuela, estación o lugar de culto sin permiso.
[[VERIFY: aprobar instrucciones nacionales para una entrada peligrosa, cerrada o inaccesible.]]

## Reúnanse a las mismas horas

{{ defaults.meetings.times_local | join(' y ') }}, hora local.
{{ defaults.meetings.if_nobody_there }} [@project_spec]

## Elijan a quien dirige

{{ defaults.convener.rule }}
{{ defaults.convener.rotation }}
{{ defaults.convener.role_fallback }} [@project_spec]

## Guion para una reunión de 15 minutos

Lean en voz alta este guion propuesto. [@project_spec]

1. «¿Quién necesita ayuda urgente? ¿Quién falta?»
2. «¿Qué peligros conocemos? Digan qué vieron y cuándo.»
3. «¿Quién puede visitar a quienes necesitan apoyo? Pidan permiso antes de entrar.»
4. «¿Qué podemos compartir? ¿Quién ayuda con agua, comida y energía segura?»
5. «Elijan una persona para cada tarea. Repitan la tarea y la próxima hora de contacto.»
6. «¿Quién dirige la próxima reunión? Repitan las horas de reunión.»

No publiquen datos médicos privados ni digan que un refugio está abierto sin confirmarlo.
[[VERIFY: probar duración, consentimiento, accesibilidad y el guion propuesto.]]
