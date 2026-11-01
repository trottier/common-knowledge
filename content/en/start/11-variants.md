---
title: How is my drive different?
status: draft
reviewer: null
reviewed_on: null
review_required: []
---

{% for number, variant in variants.variants.items() %}
## Variant {{ number }}

Planned video-library topics:
{% for topic in variant.topics %}
- {{ variants.topics[topic].title }}
{% endfor %}

Planned in-depth knowledge: {{ variants.collections[variant.collection] }}. [@project_spec]

Planned collection contents for this build:
{% for title in collection_contents[number] %}
- {{ title }}
{% else %}
No external collection files are included in this build profile.
{% endfor %}
{% endfor %}


## Why the drives differ

Every variant has the same core plan.
The full design adds video libraries for three topics and one in-depth knowledge collection.
The lists above show which external collection files this build profile selects.
Each topic is on two variants.
Each collection is on one variant. [@project_spec]

Complementary content gives neighbors a reason to find each other.
It also keeps the cost per drive down.
Ask neighbors which variant they have when it is safe to meet. [@project_spec]
