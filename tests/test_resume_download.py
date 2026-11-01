import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def download(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location(
        "resume_download", ROOT / "tools/resume_download.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps([{"id": "fixture", "url": "https://example.org/input", "size_bytes": 6}])
    )
    output = tmp_path / "input.pending"
    output.write_bytes(b"ab")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "resume_download",
            "--catalog",
            str(catalog),
            "--item",
            "fixture",
            "--output",
            str(output),
        ],
    )
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    return module, output


class Response:
    status = 206

    def __init__(self, data=b"cdef", content_range="bytes 2-5/6", etag='"fixture"'):
        self.data = data
        self.headers = {"Content-Range": content_range, "ETag": etag}

    def geturl(self):
        return "https://example.org/input"

    def read(self, limit):
        return self.data[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_resuming_retries_incomplete_ranges_without_appending_partial_data(download, monkeypatch):
    module, output = download
    calls = []

    def request(request, timeout):
        assert request.get_header("Range") == "bytes=2-5"
        assert output.read_bytes() == b"ab"
        calls.append(request)
        return Response(b"cd" if len(calls) < 3 else b"cdef")

    monkeypatch.setattr(module, "urlopen", request)
    module.main()
    assert len(calls) == 3 and output.read_bytes() == b"abcdef"


def test_wrong_range_is_rejected_before_appending(download, monkeypatch):
    module, output = download
    monkeypatch.setattr(
        module, "urlopen", lambda *args, **kwargs: Response(content_range="bytes 0-3/6")
    )
    with pytest.raises(ValueError, match="range or source size changed"):
        module.main()
    assert output.read_bytes() == b"ab"


def test_changed_source_etag_is_rejected_before_appending(download, monkeypatch):
    module, output = download
    output.with_name(output.name + ".state.json").write_text(
        json.dumps(
            {
                "url": "https://example.org/input",
                "size_bytes": 6,
                "etag": '"old"',
            }
        )
    )
    monkeypatch.setattr(module, "urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(ValueError, match="source changed"):
        module.main()
    assert output.read_bytes() == b"ab"
