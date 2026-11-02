# Explicit scene geometry cache

`SceneGeometryCache` avoids reconstructing the same source geometry during a
serial render of one immutable prepared scene. It is optional; ordinary calls
keep their existing behavior. Geometry clipping, source order, label placement,
collision checks, and coverage decisions are unchanged.

```python
from ck.countyproof import svg_map
from ck.streetlabels import SceneGeometryCache

with SceneGeometryCache(scene) as cache:
    for sheet in scene["sheets"]:
        svg, audit = svg_map(scene, sheet["bounds"], geometry_cache=cache)
```

The cache admits only that scene's original road and water geometry dictionary
objects. Its maximum membership is fixed at construction; equivalent dictionaries
from another scene are rejected. Keep geometry mappings immutable while the
context is open, and create a fresh context after changing inputs. Different
sheet bounds still compute their own intersections.

Normal and exceptional context exit clear both cached Shapely objects and source
references. The closed cache cannot be reused. There is no module/global cache,
and no cache object or Shapely geometry is added to the scene, SVG audit, or
generated receipts. Low-level functions do not enable it automatically. The full
`render` entry point accepts an explicit boolean `policy.cache_source_geometries:
true` and owns the context across that one render, including exceptional exits.
Missing or false leaves caching disabled; other types are rejected. Existing
policy files are unchanged. A separate render binding records the effective
flag, actual rendering source hashes, policy, and original preparation producer;
historical preparation recipes are preserved.

Regression checks compare complete SVG strings and complete audit dictionaries,
including source order, unnamed roads, disconnected same-name streets, water,
and unplaceable labels. They also check bounded foreign-input rejection,
exception cleanup, object release, and fresh-scene behavior. This optimization
does not clear missing labels, change review status, or establish phone acceptance.
