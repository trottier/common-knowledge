import io
import tarfile

import pytest

from ck.laptopviewer import copy_member


def sdk_archive(entries):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w:gz") as archive:
        for name, content in entries:
            member = tarfile.TarInfo(name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
    data.seek(0)
    return tarfile.open(fileobj=data, mode="r:gz")


def test_sdk_members_stay_identical_and_ambiguous_entries_fail(tmp_path):
    original = b"Publisher JavaScript\r\n/* notices */\x00"
    with sdk_archive([("package/dist/sdk.js", original)]) as archive:
        copy_member(archive, "package/dist/sdk.js", tmp_path / "sdk.js")
    assert (tmp_path / "sdk.js").read_bytes() == original
    with sdk_archive([("sdk.js", b"one"), ("sdk.js", b"two")]) as archive:
        with pytest.raises(ValueError, match="duplicated"):
            copy_member(archive, "sdk.js", tmp_path / "duplicate.js")
    assert not (tmp_path / "duplicate.js").exists()


def test_sdk_links_cannot_supply_executable_content(tmp_path):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as archive:
        member = tarfile.TarInfo("sdk.js")
        member.type, member.linkname = tarfile.SYMTYPE, "elsewhere.js"
        archive.addfile(member)
    data.seek(0)
    with tarfile.open(fileobj=data, mode="r") as archive:
        with pytest.raises(ValueError, match="unsafe"):
            copy_member(archive, "sdk.js", tmp_path / "linked.js")
    assert not (tmp_path / "linked.js").exists()
