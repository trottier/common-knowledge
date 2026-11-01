---
title: How is my drive different?
status: draft
reviewer: null
reviewed_on: null
review_required: []
---

{% for number, variant in variants.variants.items() %}
## Variant {{ number }}

Video libraries:
{% for topic in variant.topics %}
- {{ variants.topics[topic].title }}
{% endfor %}

In-depth knowledge: {{ variants.collections[variant.collection] }}. [@project_spec]

Planned collection contents for this build:
{% for title in collection_contents[number] %}
- {{ title }}
{% else %}
No external collection files are included in this build profile.
{% endfor %}
{% endfor %}

{% if not variants.offline_ai_enabled %}
Offline AI integration is deferred. Future allocation: drives {{ variants.offline_ai | join(' and ') }}. [@project_spec]
{% endif %}

## Why the drives differ

Every variant has the same core plan.
Each adds video libraries for three topics and one in-depth knowledge collection.
Each topic is on two variants.
Each collection is on one variant. [@project_spec]

Complementary content gives neighbors a reason to find each other.
It also keeps the cost per drive down.
Ask neighbors which variant they have when it is safe to meet. [@project_spec]
