"""Capacity accounting without silently omitting unconfirmed items."""

import math
from dataclasses import asdict, dataclass

from ck.catalog import Collection, Item, Topics
from ck.config import Configuration


def placed_bytes(item: Item) -> int:
    if not isinstance(item.size_bytes, int):
        raise ValueError(f"Unmeasured item: {item.id}")
    copies = 2 if item.dest.startswith(("1_START/", "4_PHONE_PACK/")) else 1
    return item.size_bytes * copies


def selected(item: Item, config: Configuration, number: int, profile: str) -> bool:
    if profile not in item.profiles or config.build.profiles[profile].third_party == "none":
        return False
    if item.family == "llm" or item.dest.startswith(("9_LOCAL_LLM/", "9_OFFLINE_AI/")):
        if not config.variants.offline_ai_enabled or number not in config.variants.offline_ai:
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
    map_path: str | None = None
    map_reason: str | None = None
    llm_variants: list[int] | None = None
    llm_reason: str | None = None

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

    choices = {
        number: [item for item in items.values() if selected(item, config, number, profile)]
        for number in sorted(config.variants.variants)
    }
    map_path, map_reason = None, None
    if profile == "full":
        map_path = "roads_places"
        map_reason = "Roads-and-places generation is explicitly configured."
        if config.build.android_maps == "auto":
            prebuilt = items.get("osmand_prebuilt")
            dependencies = {}
            if prebuilt:
                include(prebuilt, dependencies)
            ready = (
                prebuilt is not None
                and all(prebuilt in chosen for chosen in choices.values())
                and not any(item.blockers() for item in dependencies.values())
            )
            if not ready:
                map_reason = "Prebuilt maps have unconfirmed inputs or redistribution terms."
            elif any(
                core_bytes
                + sum(
                    placed_bytes(item)
                    for item in chosen
                    if item.id != "android_roads_places" and isinstance(item.size_bytes, int)
                )
                > usable
                for chosen in choices.values()
            ):
                map_reason = (
                    "Prebuilt maps overflow a variant; switch every variant to roads and places."
                )
            else:
                map_path = "prebuilt"
                map_reason = "Verified prebuilt maps fit the known capacity of every variant."
        omitted = "osmand_prebuilt" if map_path == "roads_places" else "android_roads_places"
        choices = {
            number: [item for item in chosen if item.id != omitted]
            for number, chosen in choices.items()
        }

    # Keep existing machine-readable keys while retiring universal/four-drive fallback.
    llm_variants = [
        number for number, chosen in choices.items() if any(item.family == "llm" for item in chosen)
    ]
    llm_reason = (
        "Offline AI integration is deferred; no AI items are placed."
        if not config.variants.offline_ai_enabled
        else "Offline AI placement is limited to the configured future allocation."
    )

    for number in sorted(config.variants.variants):
        chosen = choices[number]
        dependencies = {}
        for item in chosen:
            include(item, dependencies)
        problems = [issue for item in dependencies.values() for issue in item.blockers()]
        known = [item for item in chosen if isinstance(item.size_bytes, int)]
        total = core_bytes + sum(placed_bytes(item) for item in known)
        if profile == "full":
            required_map = "osmand_prebuilt" if map_path == "prebuilt" else "android_roads_places"
            for required in ("national_atlas", "national_directory", required_map):
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
                    {"id": item.id, "size_bytes": placed_bytes(item)}
                    for item in sorted(known, key=placed_bytes, reverse=True)[:8]
                ],
                sorted(set(problems)),
                map_path,
                map_reason,
                llm_variants,
                llm_reason,
            )
        )
    return plans
