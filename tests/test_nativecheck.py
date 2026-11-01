import hashlib
import io
import stat
import zipfile

import pytest

from ck.catalog import load_catalog
from ck.nativecheck import audit_native_libraries, native_members
from ck.publication import corresponding_sources


def item_from_archive(cache, identifier, members, *, apk=False):
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    original = load_catalog(root)["vlc_android" if apk else "vlc_libvlc_aar"]
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        for name, payload in members:
            archive.writestr(name, payload)
    payload = data.getvalue()
    sha = hashlib.sha256(payload).hexdigest()
    (cache / sha).write_bytes(payload)
    return original.model_copy(update={"id": identifier, "sha256": sha, "size_bytes": len(payload)})


def artifact_set(cache, *, abi="arm64-v8a", changed=False):
    app = item_from_archive(
        cache,
        "app",
        [("lib/arm64-v8a/libplayer.so", b"player"), ("lib/arm64-v8a/libc++_shared.so", b"new")],
        apk=True,
    )
    first = item_from_archive(
        cache,
        "player_artifact",
        [
            (f"jni/{abi}/libplayer.so", b"other!" if changed else b"player"),
            (f"jni/{abi}/libc++_shared.so", b"old"),
        ],
    )
    second = item_from_archive(cache, "media_artifact", [(f"jni/{abi}/libc++_shared.so", b"new")])
    return {item.id: item for item in (app, first, second)}


def test_native_members_bind_to_the_correct_component_and_never_grant_source_approval(tmp_path):
    items = artifact_set(tmp_path)
    result = audit_native_libraries(items, ["app"], ["player_artifact", "media_artifact"], tmp_path)
    bindings = {entry["library"]: entry for entry in result["applications"][0]["native_members"]}
    assert [item["artifact_id"] for item in bindings["libc++_shared.so"]["matches"]] == [
        "media_artifact"
    ]
    assert result["all_standard_native_members_match"] is True
    assert result["complete_application_source_closure"] is False
    assert result["human_license_or_pin_approval"] is False


@pytest.mark.parametrize("problem", ["changed", "wrong_abi", "tampered_cache"])
def test_unmatched_architecture_or_changed_native_bytes_fail(tmp_path, problem):
    items = artifact_set(
        tmp_path,
        abi="armeabi-v7a" if problem == "wrong_abi" else "arm64-v8a",
        changed=problem == "changed",
    )
    if problem == "tampered_cache":
        path = tmp_path / items["app"].sha256
        payload = path.read_bytes()
        path.write_bytes(payload[:-1] + bytes([payload[-1] ^ 1]))
    with pytest.raises(ValueError, match="artifact|checksum mismatch"):
        audit_native_libraries(items, ["app"], ["player_artifact", "media_artifact"], tmp_path)


def test_duplicate_or_linked_native_members_are_rejected(tmp_path):
    duplicate = tmp_path / "duplicate.zip"
    with pytest.warns(UserWarning), zipfile.ZipFile(duplicate, "w") as archive:
        archive.writestr("lib/arm64-v8a/libplayer.so", b"first")
        archive.writestr("lib/arm64-v8a/libplayer.so", b"second")
    with pytest.raises(ValueError, match="Duplicate native"):
        native_members(duplicate, "lib")
    linked = tmp_path / "linked.zip"
    with zipfile.ZipFile(linked, "w") as archive:
        info = zipfile.ZipInfo("lib/arm64-v8a/libplayer.so")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "outside.so")
    with pytest.raises(ValueError, match="Invalid native"):
        native_members(linked, "lib")


def test_empty_native_application_does_not_pass_vacuously(tmp_path):
    items = artifact_set(tmp_path)
    items["empty"] = item_from_archive(
        tmp_path, "empty", [("assets/ordinary.txt", b"text")], apk=True
    )
    with pytest.raises(ValueError, match="no standard native"):
        audit_native_libraries(items, ["empty"], ["player_artifact"], tmp_path)


def test_vlc_corresponding_sources_preserve_prior_inputs_and_exclude_compiled_aars():
    from pathlib import Path

    items = load_catalog(Path(__file__).resolve().parents[1])
    for app in ("vlc_android", "vlc_android_older"):
        sources = list(corresponding_sources(items, items[app]))
        identifiers = {item.id for item in sources}
        assert {"vlc_native_base_source", "vlc_libvlcpp_source", "vlc_sqlite_source"} <= identifiers
        assert not {"vlc_libvlc_aar", "vlc_medialibrary_aar"} & identifiers
        assert all(item.family == "docs" for item in sources)
