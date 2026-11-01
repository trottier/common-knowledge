---
title: ¿En qué se diferencia mi unidad?
status: machine
reviewer: null
reviewed_on: null
source_inputs: {"content/en/start/11-variants.md": "a4c4d264ef02758b0833d3b3a8c83219305e649c490aacddc479a685477097c6"}
review_required: []
---

Una variante es una unidad con una combinación diferente de contenido adicional.
Use las listas siguientes para comparar su unidad con otras variantes. [@project_spec]

Los nombres de los temas y las colecciones aparecen como en las carpetas en inglés.

{% for number, variant in variants.variants.items() %}
## Variante {{ number }}

Temas previstos para las bibliotecas de videos:
{% for topic in variant.topics %}
- {{ variants.topics[topic].title }}
{% endfor %}

Colección prevista de conocimientos detallados: {{ variants.collections[variant.collection] }}. [@project_spec]

Contenido previsto de la colección para esta compilación:
{% for title in collection_contents[number] %}
- {{ title }}
{% else %}
Este perfil de compilación no incluye archivos externos de la colección.
{% endfor %}
{% endfor %}


## Por qué las unidades difieren

Todas las variantes tienen el mismo plan básico.
El diseño completo añade bibliotecas de videos de tres temas y una colección de conocimientos detallados.
Las listas anteriores muestran los archivos externos de las colecciones que selecciona este perfil de compilación.
Cada tema está en dos variantes.
Cada colección está en una sola variante. [@project_spec]

El contenido complementario da a los vecinos una razón para encontrarse.
También reduce el costo de cada unidad.
Pregunte a sus vecinos qué variante tienen cuando sea seguro reunirse. [@project_spec]
