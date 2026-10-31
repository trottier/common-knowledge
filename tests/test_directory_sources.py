import csv
import io
import struct
import zipfile
from pathlib import Path

import pytest

from ck.catalog import load_catalog
from ck.directory_sources import RADIO_SERVICES, broadcast_stations, county_profiles, wgs84_point

ROOT = Path(__file__).resolve().parents[1]


def table(path, filename, rows, delimiter="|"):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter=delimiter)
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr(filename, stream.getvalue())


def test_coordinates_require_explicit_wgs84_and_reject_old_datum():
    point = struct.pack("<BIIdd", 1, 0x20000001, 4326, -71.5, 41.5).hex()
    assert wgs84_point(point) == (41.5, -71.5)
    with pytest.raises(ValueError, match="EPSG:4326"):
        wgs84_point(struct.pack("<BIIdd", 1, 0x20000001, 4267, -71.5, 41.5).hex())
    with pytest.raises(ValueError, match="Malformed"):
        wgs84_point("not coordinates")


@pytest.mark.parametrize("technical_auth", ["L", "C"])
def test_broadcast_import_follows_granted_license_reference_and_excludes_other_services(
    tmp_path, technical_auth
):
    ids = [
        "fcc_stations",
        "fcc_service_codes",
        "fcc_facility_statuses",
        "fcc_license_versions",
        "fcc_locations",
    ]
    paths = {identifier: tmp_path / identifier for identifier in ids}
    facility = {
        "active_ind": "Y",
        "facility_status": "LICEN",
        "service_code": "FM",
        "community_served_state": "RI",
        "license_filing_id": "license",
        "latest_filing_version_id": "renewal",
        "callsign": "SYNTHETIC",
        "facility_id": "1",
        "frequency": "synthetic",
        "community_served_city": "Test city",
    }
    table(
        paths["fcc_stations"],
        "facility.dat",
        [
            facility,
            {**facility, "service_code": "TV", "facility_id": "2"},
            {**facility, "facility_status": "LICAN", "facility_id": "3"},
            {
                **facility,
                "latest_filing_version_id": "permit",
                "license_filing_id": "missing",
                "facility_id": "4",
            },
        ],
    )
    table(
        paths["fcc_service_codes"],
        "lkp_service_code.dat",
        [
            {"active_ind": "Y", "service_code": code, "service_desc": code}
            for code in sorted(RADIO_SERVICES)
        ],
    )
    table(
        paths["fcc_facility_statuses"],
        "lkp_facility_status.dat",
        [{"active_ind": "Y", "facility_status": "LICEN", "facility_status_desc": "LICENSED"}],
    )
    version = {
        "filing_version_id": "renewal",
        "license_filing_id": "license",
        "active_ind": "Y",
        "service_code": "FM",
        "current_status_code": "GRA",
        "auth_type_code": "L",
        "status_date": "2026-01-01",
        "purpose_code": "REN",
        "ref_filing_version_id": "technical",
    }
    table(
        paths["fcc_license_versions"],
        "license_filing_version.dat",
        [
            version,
            {
                **version,
                "filing_version_id": "technical",
                "auth_type_code": technical_auth,
                "active_ind": "N",
                "status_date": "2020-01-01",
                "purpose_code": "L2C",
                "ref_filing_version_id": "",
            },
            {
                **version,
                "filing_version_id": "permit",
                "license_filing_id": "missing",
                "purpose_code": "CP",
                "auth_type_code": "C",
            },
        ],
    )
    table(
        paths["fcc_locations"],
        "app_location.dat",
        [
            {
                "aloc_active_ind": "Y",
                "aloc_aapp_application_id": "technical",
                "aloc_geo_coord": struct.pack("<BIIdd", 1, 0x20000001, 4326, -71.5, 41.5).hex(),
                "private_contact": "MUST NEVER BE COPIED",
            },
            {
                "aloc_active_ind": "Y",
                "aloc_aapp_application_id": "permit",
                "aloc_geo_coord": struct.pack("<BIIdd", 1, 0x20000001, 4326, -71.5, 41.5).hex(),
                "private_contact": "MUST NEVER BE COPIED",
            },
        ],
    )
    rejected = []
    places = list(broadcast_stations(paths, load_catalog(ROOT), None, rejected))
    assert len(places) == len(rejected) == 1
    assert places[0].details["Reference filing"] == "technical"
    assert places[0].longitude == -71.5
    assert "MUST NEVER BE COPIED" not in places[0].model_dump_json()
    assert rejected[0]["id"] == "fcc-4"


def test_hazard_profiles_preserve_publisher_ratings_and_report_missing_counties(tmp_path):
    source = tmp_path / "risk.zip"
    table(source, "NRI_HazardInfo.csv", [{"Prefix": "TEST", "Hazard": "Synthetic hazard"}], ",")
    table(
        source,
        "NRI_Table_Counties.csv",
        [
            {
                "STCOFIPS": "01001",
                "COUNTY": "Synthetic county",
                "STATEABBRV": "XX",
                "RISK_RATNG": "Publisher overall rating",
                "TEST_RISKR": "Publisher hazard rating",
            }
        ],
        ",",
    )
    profiles, missing = county_profiles(source, {"01001", "01002"})
    assert list(profiles) == ["01001"] and missing == ["01002"]
    assert profiles["01001"]["hazards"] == {"Synthetic hazard": "Publisher hazard rating"}
