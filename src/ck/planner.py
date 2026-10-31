"""Capacity accounting without silently omitting unconfirmed items."""

import math
from dataclasses import asdict, dataclass

from ck.catalog import Collection, Item, Topics
from ck.config import Configuration


def selected(item: Item, config: Configuration, number: int, profile: str) -> bool:
    if profile not in item.profiles or config.build.profiles[profile].third_party == "none":
        return False
    variant = config.variants.variants[number]
    if item.placement == "universal":
        return True
    if isinstance(item.placement, Topics):
        return bool(set(item.placement.topics) & set(variant.topics))
    if isinstance(item.placement, Collection):
        return item.placement.collection == variant.collection
    return False


@dataclass
class VariantPlan:
    variant: int
    capacity_bytes: int
    usable_bytes: int
    core_bytes: int
    known_total_bytes: int
    items: list[str]
    largest: list[dict]
    blockers: list[str]

    @property
    def fits(self) -> bool:
        return not self.blockers and self.known_total_bytes <= self.usable_bytes

    def as_dict(self):
        return {**asdict(self), "fits": self.fits}


def plan_variants(
    config: Configuration,
    items: dict[str, Item],
    profile: str,
    core_bytes: int,
    capacity_override: int | None = None,
) -> list[VariantPlan]:
    if profile not in config.build.profiles:
        raise ValueError(f"Unknown profile: {profile}")
    spec = config.build.profiles[profile]
    capacity = (
        capacity_override
        if capacity_override is not None
        else (spec.image_size_mib * 1024 * 1024 if spec.image_size_mib else spec.capacity_bytes)
    )
    if type(capacity) is not int or capacity <= 0:
        raise ValueError(f"Measured production capacity is unconfirmed: {capacity}")
    usable = math.floor(capacity * (1 - spec.reserve_fraction))
    plans = []

    def include(item, dependencies):
        if item.id in dependencies:
            return
        dependencies[item.id] = item
        for identifier in item.inputs:
            include(items[identifier], dependencies)

    for number in sorted(config.variants.variants):
        chosen = [item for item in items.values() if selected(item, config, number, profile)]
        dependencies = {}
        for item in chosen:
            include(item, dependencies)
        problems = [issue for item in dependencies.values() for issue in item.blockers()]
        known = [item for item in chosen if isinstance(item.size_bytes, int)]
        total = core_bytes + sum(item.size_bytes for item in known)
        if profile == "full":
            for required in ("national_atlas", "national_directory", "android_roads_places"):
                if required not in {item.id for item in chosen}:
                    problems.append(f"Required universal item is missing: {required}")
        if total > usable:
            problems.append(f"Overflow: {total - usable} bytes; move items explicitly in catalog")
        plans.append(
            VariantPlan(
                number,
                capacity,
                usable,
                core_bytes,
                total,
                sorted(item.id for item in chosen),
                [
                    {"id": item.id, "size_bytes": item.size_bytes}
                    for item in sorted(known, key=lambda x: x.size_bytes, reverse=True)[:8]
                ],
                sorted(set(problems)),
            )
        )
    return plans
