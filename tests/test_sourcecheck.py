import hashlib
from pathlib import Path

import blake3
import pytest

from ck.catalog import load_catalog
from ck.config import load_config
from ck.sourcecheck import verify_publisher_input

ROOT = Path(__file__).resolve().parents[1]


def test_publisher_checksum_rejects_same_size_tampering_and_wrong_pmtiles_header(tmp_path):
    item = load_catalog(ROOT, load_config(ROOT))["protomaps_planet"].model_copy(deep=True)
    payload = b"PMTiles\x03Synthetic test payload"
    item.size_bytes = len(payload)
    item.sha256 = hashlib.sha256(payload).hexdigest()
    item.publisher_blake3 = blake3.blake3(payload).hexdigest()
    source = tmp_path / "source"
    source.write_bytes(payload)
    assert verify_publisher_input(item, source)["sha256"] == item.sha256
    source.write_bytes(payload[:-1] + b"!")
    with pytest.raises(ValueError, match="BLAKE3"):
        verify_publisher_input(item, source)
    source.write_bytes(b"Wrong!!\x03" + payload[8:])
    with pytest.raises(ValueError, match="header"):
        verify_publisher_input(item, source)
