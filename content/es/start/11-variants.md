---
title: ¿Por qué mi unidad es diferente?
status: machine
reviewer: null
reviewed_on: null
source_inputs: {"content/en/start/11-variants.md": "2f533ff1a0c616517148860703dbaf3273d4e006939bbc37b1e8e61d2da2ce0d"}
review_required: []
---

## El mismo contenido básico, con distintos temas de ampliación

Todas las variantes tienen el mismo contenido básico.
Cada una añade tres módulos y una sección de biblioteca.
Cada módulo está en dos variantes.
Pregunte a sus vecinos qué variante tienen cuando sea seguro reunirse. [@project_spec]

Los nombres de los módulos y de las secciones de biblioteca aparecen como en las carpetas en inglés.

{% for number, variant in variants.variants.items() %}
## Variante {{ number }}

{% for module in variant.modules %}
- {{ variants.modules[module].title }}
{% endfor %}

Biblioteca: {{ variants.shelves[variant.shelf] }}. [@project_spec]

Contenido previsto de la biblioteca para esta compilación:
{% for title in shelf_contents[number] %}
- {{ title }}
{% else %}
Este perfil de compilación no incluye archivos externos de biblioteca.
{% endfor %}
{% endfor %}
