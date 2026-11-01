---
title: ¿En qué se diferencia mi unidad?
status: machine
reviewer: null
reviewed_on: null
source_inputs: {"content/en/start/11-variants.md": "9b1f4bfa8a64a5b630341c0aa681c5fd01039504cc1040e0af5f13e1ad248c0d"}
review_required: []
---

Los nombres de los temas y las colecciones aparecen como en las carpetas en inglés.

{% for number, variant in variants.variants.items() %}
## Variante {{ number }}

Bibliotecas de videos:
{% for topic in variant.topics %}
- {{ variants.topics[topic].title }}
{% endfor %}

Conocimientos detallados: {{ variants.collections[variant.collection] }}. [@project_spec]

Contenido previsto de la colección para esta compilación:
{% for title in collection_contents[number] %}
- {{ title }}
{% else %}
Este perfil de compilación no incluye archivos externos de la colección.
{% endfor %}
{% endfor %}

## Por qué las unidades difieren

Todas las variantes tienen el mismo plan básico.
Cada una añade bibliotecas de videos de tres temas y una colección de conocimientos detallados.
Cada tema está en dos variantes.
Cada colección está en una sola variante. [@project_spec]

El contenido complementario da a los vecinos una razón para encontrarse.
También reduce el costo de cada unidad.
Pregunte a sus vecinos qué variante tienen cuando sea seguro reunirse. [@project_spec]
