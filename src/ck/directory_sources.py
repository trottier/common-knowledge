"""Read only public broadcast references and historical county hazard ratings."""

import csv
import io
import math
import re
import struct
import zipfile
from collections import defaultdict
from pathlib import Path

from ck.catalog import Item

RADIO_SERVICES = {"AM", "FM", "FL", "FX", "FB"}


def zip_rows(path: Path, filename: str, delimiter: str = ","):
    with zipfile.ZipFile(path) as archive:
        if archive.namelist().count(filename) != 1:
            raise ValueError(f"Publisher archive must contain exactly one {filename}")
        with archive.open(filename) as stream:
            yield from csv.DictReader(
                io.TextIOWrapper(stream, encoding="utf-8-sig"), delimiter=delimiter
            )


def wgs84_point(value: str) -> tuple[float, float]:
    """Require the publisher's explicit EPSG:4326 point; never relabel NAD27 DMS."""
    try:
        payload = bytes.fromhex(value)
        order = {0: ">", 1: "<"}[payload[0]]
        geometry, srid, longitude, latitude = struct.unpack(order + "IIdd", payload[1:])
    except (ValueError, KeyError, IndexError, struct.error) as error:
        raise ValueError("Malformed FCC geographic point") from error
    if geometry != 0x20000001 or srid != 4326:
        raise ValueError("FCC geographic point must declare EPSG:4326")
    if not (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    ):
        raise ValueError("Invalid FCC geographic coordinates")
    return latitude, longitude


def broadcast_stations(
    paths: dict[str, Path], items: dict[str, Item], state: str | None, rejected: list
):
    from ck.directory import Place

    services = {
        row["service_code"]: row["service_desc"]
        for row in zip_rows(paths["fcc_service_codes"], "lkp_service_code.dat", "|")
        if row["active_ind"] == "Y"
    }
    statuses = {
        row["facility_status"]: row["facility_status_desc"]
        for row in zip_rows(paths["fcc_facility_statuses"], "lkp_facility_status.dat", "|")
        if row["active_ind"] == "Y"
    }
    if not RADIO_SERVICES <= services.keys() or statuses.get("LICEN") != "LICENSED":
        raise ValueError("FCC service or license status dictionary changed")
    facilities = [
        row
        for row in zip_rows(paths["fcc_stations"], "facility.dat", "|")
        if row["active_ind"] == "Y"
        and row["facility_status"] == "LICEN"
        and row["service_code"] in RADIO_SERVICES
        and (state is None or row["community_served_state"] == state)
    ]
    license_ids = {row["license_filing_id"] for row in facilities}
    versions = {}
    by_license = defaultdict(list)
    for row in zip_rows(paths["fcc_license_versions"], "license_filing_version.dat", "|"):
        if (
            row["license_filing_id"] in license_ids
            and row["service_code"] in RADIO_SERVICES
            and row["auth_type_code"] in {"L", "C"}
            and row["current_status_code"] == "GRA"
        ):
            selected = {
                key: row[key]
                for key in (
                    "filing_version_id",
                    "license_filing_id",
                    "active_ind",
                    "current_status_code",
                    "auth_type_code",
                    "status_date",
                    "purpose_code",
                    "ref_filing_version_id",
                )
            }
            versions[row["filing_version_id"]] = selected
            by_license[row["license_filing_id"]].append(selected)
    locations = defaultdict(list)
    for row in zip_rows(paths["fcc_locations"], "app_location.dat", "|"):
        if (
            row["aloc_active_ind"] == "Y"
            and row["aloc_aapp_application_id"] in versions
            and row["aloc_geo_coord"]
        ):
            locations[row["aloc_aapp_application_id"]].append(row["aloc_geo_coord"])
    for facility in sorted(facilities, key=lambda row: (row["callsign"], row["facility_id"])):
        # Prefer the facility's own filing. Otherwise follow the most recent
        # granted license reference. A granted construction permit supplies
        # geometry only when a granted license explicitly references it.
        # Never infer a station site from a nearby POI or community centroid.
        candidates = [
            row
            for row in by_license[facility["license_filing_id"]]
            if row["active_ind"] == "Y"
            and row["current_status_code"] == "GRA"
            and row["auth_type_code"] == "L"
        ]
        candidates.sort(
            key=lambda row: (row["status_date"], row["filing_version_id"]), reverse=True
        )
        selected = None
        for identifier in [
            facility["latest_filing_version_id"],
            *[row["filing_version_id"] for row in candidates],
        ]:
            visited = set()
            while identifier and identifier not in visited:
                visited.add(identifier)
                version = versions.get(identifier)
                if (
                    not version
                    or version["auth_type_code"] not in ({"L"} if len(visited) == 1 else {"L", "C"})
                    or version["current_status_code"] != "GRA"
                ):
                    break
                if locations[identifier]:
                    # Historical technical filings are accepted only when the
                    # current license explicitly references them, or the filing
                    # itself grants a license to cover / license modification.
                    if (
                        len(visited) > 1
                        or identifier == facility["latest_filing_version_id"]
                        or version["purpose_code"] in {"L2C", "MOD"}
                    ):
                        selected = identifier
                        break
                identifier = version["ref_filing_version_id"]
            if selected:
                break
        if not selected:
            rejected.append(
                {
                    "id": "fcc-" + facility["facility_id"],
                    "state": facility["community_served_state"],
                    "reason": "No unambiguous granted-license geographic reference",
                    "callsign": facility["callsign"],
                    "service": facility["service_code"],
                    "frequency": facility["frequency"],
                    "community": facility["community_served_city"],
                }
            )
            continue
        points = sorted({wgs84_point(value) for value in locations[selected]})
        for index, (latitude, longitude) in enumerate(points, 1):
            yield Place(
                id=f"fcc-{facility['facility_id']}-{index}",
                category="broadcast_station",
                name=facility["callsign"],
                address="",
                latitude=latitude,
                longitude=longitude,
                source_id="fcc_stations",
                as_of=items["fcc_stations"].version,
                details={
                    "Service": services[facility["service_code"]],
                    "FCC frequency field": facility["frequency"],
                    "Community served": facility["community_served_city"]
                    + ", "
                    + facility["community_served_state"],
                    "Reference filing": selected,
                    "Access": "Licensed broadcast reference; public access is not implied",
                },
            )


def county_profiles(path: Path, county_codes: set[str]) -> tuple[dict, list[str]]:
    hazards = list(zip_rows(path, "NRI_HazardInfo.csv"))
    if not hazards or any(
        not re.fullmatch(r"[A-Z]{4}", row["Prefix"]) or not row["Hazard"] for row in hazards
    ):
        raise ValueError("FEMA hazard dictionary schema changed")
    profiles = {}
    for row in zip_rows(path, "NRI_Table_Counties.csv"):
        code = row["STCOFIPS"]
        if not re.fullmatch(r"\d{5}", code):
            raise ValueError("FEMA county identifier must be five digits")
        if code not in county_codes:
            continue
        if code in profiles:
            raise ValueError("Duplicate FEMA county profile")
        profiles[code] = {
            "county": row["COUNTY"],
            "state": row["STATEABBRV"],
            "risk_rating": row["RISK_RATNG"],
            "hazards": {hazard["Hazard"]: row[hazard["Prefix"] + "_RISKR"] for hazard in hazards},
        }
    return profiles, sorted(county_codes - profiles.keys())
