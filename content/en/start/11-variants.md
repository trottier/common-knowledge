---
title: Why is my drive different?
status: draft
reviewer: null
reviewed_on: null
review_required: []
---

## Same core, different depth

Every variant has the same core.
Each adds three modules and one library shelf.
Each module is on two variants.
Ask neighbors which variant they have when it is safe to meet. [@project_spec]

{% for number, variant in variants.variants.items() %}
## Variant {{ number }}

{% for module in variant.modules %}
- {{ variants.modules[module].title }}
{% endfor %}

Shelf: {{ variants.shelves[variant.shelf] }}. [@project_spec]
{% endfor %}

[[VERIFY: append each shelf's actual catalog contents from the capacity plan at assembly time.]]
