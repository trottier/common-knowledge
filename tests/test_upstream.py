from datetime import date

import pytest

from ck.catalog import Item
from ck.upstream import upstream_blockers

TODAY = date(2026, 11, 1)


def item(**changes):
    data = dict(
        id="fixture",
        family="docs",
        title="Synthetic fixture",
        version="1",
        url="https://example.invalid/download",
        size_bytes=1,
        sha256="a" * 64,
        license="CC0-1.0",
        attribution="Original test fixture",
        license_proof_url="https://example.invalid/license",
        placement="hub_only",
        dest="build/fixture",
        profiles=["sample"],
        release_date="2026-10-01",
        release_date_source_url="https://example.invalid/release",
        security_advisories={
            "checked_on": "2026-11-01",
            "status": "clear",
            "source_urls": ["https://example.invalid/security"],
        },
    )
    data.update(changes)
    return Item.model_validate(data)


def test_exact_waiting_period_and_future_releases():
    assert upstream_blockers([item()], 31, as_of=TODAY) == []
    assert "requires 32" in upstream_blockers([item()], 32, as_of=TODAY)[0]
    assert "future" in upstream_blockers([item(release_date="2026-11-02")], 0, as_of=TODAY)[0]


@pytest.mark.parametrize("threshold", ["[[VERIFY: set by maintainers]]", -1, True])
def test_unconfirmed_policy_fails_even_with_no_downloads(threshold):
    assert "confirmed by maintainers" in upstream_blockers([], threshold, as_of=TODAY)[0]


def test_missing_dates_sources_and_advisory_evidence_stay_blocked():
    problems = upstream_blockers(
        [item(release_date=None, release_date_source_url=None, security_advisories=None)],
        0,
        as_of=TODAY,
    )
    assert len(problems) == 3


@pytest.mark.parametrize(
    "status,urls",
    [
        ("open", []),
        ("unreviewed", []),
        ("clear", ["https://example.invalid/advisory"]),
    ],
)
def test_open_or_unknown_advisories_cannot_be_cleared_by_a_label(status, urls):
    record = item(
        security_advisories={
            "checked_on": "2026-11-01",
            "status": status,
            "source_urls": ["https://example.invalid/security"],
            "advisory_urls": urls,
        }
    )
    assert "open or unreviewed" in upstream_blockers([record], 0, as_of=TODAY)[0]


@pytest.mark.parametrize("checked_on", ["2026-09-30", "2026-11-02"])
def test_advisory_check_must_follow_release_and_not_be_in_future(checked_on):
    record = item(
        security_advisories={
            "checked_on": checked_on,
            "status": "clear",
            "source_urls": ["https://example.invalid/security"],
        }
    )
    assert "date is invalid" in upstream_blockers([record], 0, as_of=TODAY)[0]


def test_an_early_advisory_check_does_not_cover_the_waiting_period():
    record = item(
        security_advisories={
            "checked_on": "2026-10-15",
            "status": "clear",
            "source_urls": ["https://example.invalid/security"],
        }
    )
    assert "date is invalid" in upstream_blockers([record], 31, as_of=TODAY)[0]


def test_generated_outputs_use_their_input_dates_and_historical_drafts_remain_valid():
    generated = item(
        family="generated",
        url=None,
        inputs=["fixture_input"],
        pipeline_version="fixture-1",
        release_date=None,
        release_date_source_url=None,
        security_advisories=None,
    )
    assert upstream_blockers([generated], 31, as_of=TODAY) == []
    draft = item(release_date=None, release_date_source_url=None, security_advisories=None)
    assert draft.blockers() == []
