"""Offline release checks over documented upstream dates and advisory evidence.

These checks do not query an advisory service or create a security approval.
Missing evidence stays a blocker; existing draft cache reuse remains separate.
"""

from collections.abc import Iterable
from datetime import UTC, date, datetime

from ck.catalog import Item


def upstream_blockers(
    items: Iterable[Item], minimum_age_days: int | str, *, as_of: date | None = None
) -> list[str]:
    today = as_of if as_of is not None else datetime.now(UTC).date()
    if type(minimum_age_days) is not int or minimum_age_days < 0:
        return ["config/build.yaml: upstream_min_age_days must be confirmed by maintainers"]
    problems = []
    for item in items:
        if item.family == "generated":
            continue  # Its downloaded inputs are checked individually.
        prefix = item.id + ": upstream "
        if not isinstance(item.release_date, date):
            problems.append(prefix + "release date is unconfirmed")
        else:
            age = (today - item.release_date).days
            if age < 0:
                problems.append(prefix + "release date is in the future")
            elif age < minimum_age_days:
                problems.append(prefix + f"release is {age} days old; requires {minimum_age_days}")
        if not item.release_date_source_url or "[[VERIFY" in item.release_date_source_url:
            problems.append(prefix + "release date needs a publisher source URL")
        check = item.security_advisories
        if check is None:
            problems.append(prefix + "security advisory check is missing")
            continue
        if check.status != "clear" or check.advisory_urls:
            problems.append(prefix + "security advisories are open or unreviewed")
        if check.checked_on > today or (
            isinstance(item.release_date, date)
            and (check.checked_on - item.release_date).days < minimum_age_days
        ):
            problems.append(prefix + "security advisory check date is invalid")
    return problems
