"""Create and verify deterministic FAT32 images without mounting them."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ck.assemble import check_manifest
from ck.config import Configuration
from ck.drive_safety import validate_tree
from ck.fat import normalize_fat_timestamps
from ck.fetch import digest


def run(command: list[str], epoch: int) -> subprocess.CompletedProcess:
    environment = {
        **os.environ,
        "TZ": "UTC",
        "LC_ALL": "C.UTF-8",
        "SOURCE_DATE_EPOCH": str(epoch),
        "MTOOLS_SKIP_CHECK": "1",
        "MTOOLSRC": "/dev/null",
    }
    try:
        return subprocess.run(command, env=environment, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        raise ValueError(f"{command[0]} failed: {error.stderr.strip()}") from error


def verify_image(image: Path, epoch: int, expected_manifest_sha: str | None = None) -> None:
    with tempfile.TemporaryDirectory(prefix="ck-image-verify-") as temporary:
        extracted = Path(temporary)
        run(["mcopy", "-s", "-m", "-i", str(image), "::/*", str(extracted)], epoch)
        if expected_manifest_sha and digest(extracted / "MANIFEST.SHA256") != expected_manifest_sha:
            raise ValueError("Image manifest differs from the published external hash")
        check_manifest(extracted)


def build_image(
    tree: Path,
    output: Path,
    config: Configuration,
    number: int,
    profile: str,
    epoch: int,
    compress: bool = True,
) -> dict[str, str]:
    check_manifest(tree)
    files = validate_tree(tree)
    spec = config.build.profiles[profile]
    capacity = spec.image_size_mib * 1024 * 1024 if spec.image_size_mib else spec.capacity_bytes
    if type(capacity) is not int:
        raise ValueError("Measured production capacity is unconfirmed")
    output.mkdir(parents=True, exist_ok=True)
    name = f"common-knowledge-{config.build.version}-variant-{number}-{profile}.img"
    image = output / name
    if image.exists() or image.with_suffix(".img.zst").exists():
        raise ValueError("Image output exists; choose a clean output directory")
    with tempfile.TemporaryDirectory(dir=output, prefix=".ck-image-") as temporary:
        staging = Path(temporary) / name
        run(
            [
                "mkfs.fat",
                "--invariant",
                "-F",
                "32",
                "-n",
                config.build.volume_label,
                "-i",
                config.build.volume_id,
                "-C",
                str(staging),
                str(capacity // 1024),
            ],
            epoch,
        )
        directories = sorted(
            (path for path in tree.rglob("*") if path.is_dir()),
            key=lambda path: (len(path.relative_to(tree).parts), path.relative_to(tree).as_posix()),
        )
        for directory in directories:
            run(["mmd", "-i", str(staging), "::/" + directory.relative_to(tree).as_posix()], epoch)
        for file in sorted(files, key=lambda path: path.relative_to(tree).as_posix()):
            run(
                [
                    "mcopy",
                    "-m",
                    "-Q",
                    "-i",
                    str(staging),
                    str(file),
                    "::/" + file.relative_to(tree).as_posix(),
                ],
                epoch,
            )
        if (tree / "BACKUP").is_dir():
            run(["mattrib", "-i", str(staging), "+h", "::/BACKUP"], epoch)
        normalize_fat_timestamps(staging, epoch)
        listing = run(["mdir", "-a", "-/", "-i", str(staging), "::/"], epoch).stdout
        manifest_sha = digest(tree / "MANIFEST.SHA256")
        verify_image(staging, epoch, manifest_sha)
        staging.rename(image)
    image_hash = digest(image)
    image.with_suffix(".img.sha256").write_text(f"{image_hash}  {image.name}\n")
    image.with_suffix(".listing.txt").write_text(listing, encoding="utf-8")
    manifest = image.with_suffix(".MANIFEST.SHA256")
    shutil.copyfile(tree / "MANIFEST.SHA256", manifest)
    manifest.with_suffix(".SHA256.sha256").write_text(f"{manifest_sha}  {manifest.name}\n")
    result = {
        "image": str(image),
        "sha256": image_hash,
        "manifest": str(manifest),
        "manifest_sha256": manifest_sha,
    }
    if compress:
        compressed = image.with_suffix(".img.zst")
        run(["zstd", "-19", "-T1", "--no-progress", str(image), "-o", str(compressed)], epoch)
        compressed_hash = digest(compressed)
        compressed.with_suffix(".zst.sha256").write_text(f"{compressed_hash}  {compressed.name}\n")
        result.update(compressed=str(compressed), compressed_sha256=compressed_hash)
    return result
