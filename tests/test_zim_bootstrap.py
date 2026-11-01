import importlib.util
import io
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bootstrap_zim", ROOT / "tools/bootstrap_zim.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize("name", ["../zimcheck", "/bin/zimcheck"])
def test_unsafe_checker_paths_are_rejected(name):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:gz") as archive:
        entry = tarfile.TarInfo(name)
        entry.size = 7
        archive.addfile(entry, io.BytesIO(b"fixture"))
    with pytest.raises(ValueError, match="Unsafe"):
        MODULE.checker(raw.getvalue())


def test_checker_must_be_one_regular_file():
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:gz") as archive:
        entry = tarfile.TarInfo("bin/zimcheck")
        entry.type = tarfile.SYMTYPE
        entry.linkname = "../elsewhere"
        archive.addfile(entry)
    with pytest.raises(ValueError, match="regular"):
        MODULE.checker(raw.getvalue())
