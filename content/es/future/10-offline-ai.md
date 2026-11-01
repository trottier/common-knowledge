---
title: IA sin conexión — futura
status: machine
reviewer: null
reviewed_on: null
source_inputs: {"content/en/future/10-offline-ai.md": "ced17e5cffeb1b41e438799db7c59f2ed0034d531c0abafd83b9f4678af37d65"}
review_required: [medical]
---

## IA sin conexión — futura

{% if not variants.offline_ai_enabled %}
La integración de la IA sin conexión está aplazada.
Asignación futura: unidades {{ variants.offline_ai | join(' y ') }}. [@project_spec]
{% endif %}
