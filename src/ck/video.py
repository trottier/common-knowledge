"""Reproducible imported video normalization with separate subtitle tracks."""

import hashlib
import json
import math
import re
import struct
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, model_validator

from ck.catalog import Item, safe_path
from ck.config import Configuration, Identifier, Model, read_yaml
from ck.generated import cached_input, generation_manifest


class Subtitle(Model):
    language: str
    source_id: Identifier
    stream: int = Field(default=0, ge=0)
    time_offset_seconds: float = Field(default=0, allow_inf_nan=False)


class Clip(Model):
    source_id: Identifier
    filename: str
    audio_languages: list[str] = Field(min_length=1)
    subtitles: list[Subtitle] = Field(default_factory=list)

    @model_validator(mode="after")
    def names(self):
        if len(safe_path(self.filename).parts) != 1 or not self.filename.endswith(".mp4"):
            raise ValueError("A clip needs one FAT-safe MP4 filename")
        languages = [track.language for track in self.subtitles]
        if len(set(languages)) != len(languages) or len(set(self.audio_languages)) != len(
            self.audio_languages
        ):
            raise ValueError("A clip cannot have duplicate language tracks")
        if self.audio_languages[0] != "en":
            raise ValueError("Imported clips must retain English original audio first")
        if any(
            track.source_id == self.source_id and track.time_offset_seconds
            for track in self.subtitles
        ):
            raise ValueError("An embedded subtitle cannot shift its shared picture/audio input")
        return self


class VideoSettings(Model):
    width: int = Field(ge=2, multiple_of=2)
    height: int = Field(ge=2, multiple_of=2)
    fps: int = Field(ge=1)
    video_bitrate: int = Field(gt=0)
    audio_bitrate: int = Field(gt=0)
    audio_sample_rate: int = Field(gt=0)
    language_codes_id: Identifier


def video_rights_allowed(item: Item) -> bool:
    """Recognize intake providers; per-item rights and human review still apply.

    DVIDS' official embed pages publish this particular CDN and path shape.
    Its public-domain statement has exceptions, so the catalog proof must name
    the specific video page rather than the provider's general copyright page.
    """
    source = urlparse(item.url or "")
    proof = urlparse(item.license_proof_url)
    host, proof_host = source.hostname or "", proof.hostname or ""
    federal = host.endswith(".gov") or proof_host.endswith(".gov")
    commons = host == "upload.wikimedia.org" and proof_host == "commons.wikimedia.org"
    dvids = (
        source.netloc == "d34w7g4gy10iej.cloudfront.net"
        and proof.netloc == "www.dvidshub.net"
        and not any((source.query, source.fragment, proof.query, proof.fragment))
        and re.fullmatch(r"/video/[0-9]{4}/(DOD_[0-9]+)/\1\.mp4", source.path) is not None
        and re.fullmatch(r"/video/[0-9]+/[a-z0-9-]+", proof.path) is not None
    )
    return ((federal or dvids) and item.license == "US-PD") or (
        commons
        and item.license in {"CC0-1.0", "CC-BY-3.0", "CC-BY-4.0", "CC-BY-SA-4.0", "CC-BY-SA-3.0"}
    )


def language_codes(path: Path, config: Configuration) -> dict[str, str]:
    codes = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        parts = line.split("|")
        if len(parts) != 5:
            raise ValueError("Unexpected ISO 639-2 table format")
        if parts[2]:
            codes[parts[2]] = parts[1] or parts[0]
    result = {}
    for edition in config.languages:
        base = edition.code.split("-")[0]
        if base not in codes:
            raise ValueError(f"No ISO 639-2 code for {edition.code}")
        result[edition.code] = codes[base]
    return result


def probe(path: Path) -> dict:
    report = json.loads(
        subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    report["format"].pop("filename", None)
    return report


def check_faststart(path: Path) -> None:
    atoms = []
    total = path.stat().st_size
    with path.open("rb") as stream:
        while stream.tell() < total:
            start = stream.tell()
            header = stream.read(8)
            if len(header) != 8:
                raise ValueError("Truncated MP4 atom")
            size, kind = struct.unpack(">I4s", header)
            if size == 1:
                extended = stream.read(8)
                if len(extended) != 8:
                    raise ValueError("Truncated MP4 extended atom")
                size = struct.unpack(">Q", extended)[0]
            elif size == 0:
                size = total - start
            if size < stream.tell() - start or start + size > total:
                raise ValueError("Invalid MP4 atom size")
            atoms.append(kind)
            stream.seek(start + size)
    if b"moov" not in atoms or b"mdat" not in atoms or atoms.index(b"moov") > atoms.index(b"mdat"):
        raise ValueError("MP4 needs faststart metadata before picture data")


def packet_end(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_packets",
            "-protocol_whitelist",
            "file,pipe",
            "-show_entries",
            "packet=codec_type,pts_time,duration_time",
            "-of",
            "compact=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    ends = []
    for line in result.stdout.splitlines():
        values = dict(part.split("=", 1) for part in line.split("|") if "=" in part)
        if (
            values.get("codec_type") in {"video", "audio"}
            and values.get("pts_time", "N/A") != "N/A"
        ):
            duration = values.get("duration_time", "0")
            end = float(values["pts_time"]) + (0 if duration == "N/A" else float(duration))
            if not math.isfinite(end):
                raise ValueError("Non-finite media timestamp")
            ends.append(end)
    if not ends:
        raise ValueError("Source has no timed media packets")
    return max(ends)


def subtitle_bounds(
    path: Path, stream: int, offset: float, media_end: float, origin: float = 0
) -> dict:
    """Reject missing, untimed or out-of-range captions before video encoding.

    Publisher caption files sometimes retain an editor's timeline instead of
    the downloadable clip's clock. A configured shift must be explicit; never
    infer one or trim cues silently to make a file fit.
    """
    report = json.loads(
        subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-select_streams",
                f"s:{stream}",
                "-show_packets",
                "-show_entries",
                "packet=pts_time,duration_time",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    packets = report.get("packets", [])
    if not packets:
        raise ValueError("Declared subtitle stream has no timed cues")
    starts, ends = [], []
    for packet in packets:
        try:
            start = float(packet["pts_time"]) + offset - origin
            duration = float(packet["duration_time"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Subtitle cue has no valid timing") from error
        end = start + duration
        if not all(math.isfinite(value) for value in (start, duration, end)) or duration <= 0:
            raise ValueError("Subtitle cue has no valid timing")
        # A millisecond permits only container timestamp rounding, not a
        # clipped sentence or an unreviewed automatic alignment adjustment.
        if start < -0.001 or end > media_end + 0.001:
            raise ValueError(
                "Subtitle cue is outside the original media timeline; "
                "confirm an explicit caption offset instead of dropping cues"
            )
        starts.append(start)
        ends.append(end)
    return {
        "stream": stream,
        "time_offset_seconds": offset,
        "input_origin_seconds": origin,
        "cues": len(packets),
        "first_seconds": min(starts),
        "last_seconds": max(ends),
    }


def validate_video(
    report: dict, clip: Clip, settings: VideoSettings, codes: dict[str, str], order: list[str]
) -> None:
    streams = report["streams"]
    pictures = [stream for stream in streams if stream["codec_type"] == "video"]
    audio = [stream for stream in streams if stream["codec_type"] == "audio"]
    subtitles = [stream for stream in streams if stream["codec_type"] == "subtitle"]
    if len(pictures) != 1 or len(streams) != 1 + len(audio) + len(subtitles):
        raise ValueError("A video must have exactly one picture track and no extra data streams")
    picture = pictures[0]
    if (
        picture["codec_name"] != "h264"
        or picture["profile"] != "Main"
        or picture["pix_fmt"] != "yuv420p"
        or picture["width"] != settings.width
        or picture["height"] != settings.height
        or picture["avg_frame_rate"] != f"{settings.fps}/1"
    ):
        raise ValueError("Video picture does not match the drive specification")
    expected_audio = sorted(clip.audio_languages, key=order.index)
    expected_subtitles = sorted((track.language for track in clip.subtitles), key=order.index)
    for actual, expected, kind in (
        (audio, expected_audio, "audio"),
        (subtitles, expected_subtitles, "subtitle"),
    ):
        if len(actual) != len(expected):
            raise ValueError(f"Missing {kind} tracks")
        for stream, language in zip(actual, expected, strict=True):
            if stream.get("tags", {}).get("language") != codes[language]:
                raise ValueError(f"Incorrect {kind} language or track order")
            if kind == "audio" and (
                stream["codec_name"] != "aac"
                or stream["channels"] != 1
                or int(stream["sample_rate"]) != settings.audio_sample_rate
            ):
                raise ValueError("Audio must be mono AAC")
            if kind == "subtitle" and stream["codec_name"] != "mov_text":
                raise ValueError("Subtitles must remain separate mov_text tracks")
    if not audio or audio[0].get("disposition", {}).get("default") != 1:
        raise ValueError("The first English audio track must be the default")
    if any(stream.get("disposition", {}).get("default") for stream in audio[1:]):
        raise ValueError("Only the first audio track may be the default")


def normalize(
    clip: Clip,
    paths: dict[str, Path],
    target: Path,
    settings: VideoSettings,
    codes: dict[str, str],
    names: dict[str, str],
    epoch: int,
) -> dict:
    order = list(names)
    languages = [*clip.audio_languages, *(track.language for track in clip.subtitles)]
    if not set(languages) <= codes.keys():
        raise ValueError("A video track has an unknown edition language")
    source = probe(paths[clip.source_id])
    source_audio = [s for s in source["streams"] if s["codec_type"] == "audio"]
    source_subtitles = [s for s in source["streams"] if s["codec_type"] == "subtitle"]
    if len(source_audio) != len(clip.audio_languages):
        raise ValueError("Declare every original audio track; none may be silently dropped")
    for stream, language in zip(source_audio, clip.audio_languages, strict=True):
        original_language = stream.get("tags", {}).get("language", "und")
        if original_language not in {"und", "", codes[language]}:
            raise ValueError("Original audio language disagrees with the clip declaration")
    source_end = packet_end(paths[clip.source_id]) - float(source["format"].get("start_time", 0))
    embedded = {t.stream for t in clip.subtitles if t.source_id == clip.source_id}
    if embedded != set(range(len(source_subtitles))):
        raise ValueError("Declare every embedded subtitle track")
    caption_audits = [
        {
            "language": track.language,
            "source_id": track.source_id,
            **subtitle_bounds(
                paths[track.source_id],
                track.stream,
                track.time_offset_seconds,
                source_end,
                float(source["format"].get("start_time", 0))
                if track.source_id == clip.source_id
                else 0,
            ),
        }
        for track in clip.subtitles
    ]
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-nostdin",
        "-n",
        "-fflags",
        "+bitexact",
        "-protocol_whitelist",
        "file,pipe",
        "-i",
        str(paths[clip.source_id]),
    ]
    subtitles = sorted(clip.subtitles, key=lambda track: order.index(track.language))
    subtitle_maps = []
    next_input = 1
    for track in subtitles:
        if track.source_id == clip.source_id:
            subtitle_maps.append(f"0:s:{track.stream}")
        else:
            command += [
                "-protocol_whitelist",
                "file,pipe",
                "-itsoffset",
                str(track.time_offset_seconds),
                "-i",
                str(paths[track.source_id]),
            ]
            subtitle_maps.append(f"{next_input}:s:{track.stream}")
            next_input += 1
    command += ["-map", "0:v:0"]
    audio_languages = sorted(enumerate(clip.audio_languages), key=lambda pair: order.index(pair[1]))
    for index, _ in audio_languages:
        command += ["-map", f"0:a:{index}"]
    for mapping in subtitle_maps:
        command += ["-map", mapping]
    filters = (
        f"scale={settings.width}:{settings.height}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
        f"pad={settings.width}:{settings.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={settings.fps}"
    )
    command += [
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-vf",
        filters,
        "-c:v",
        "libx264",
        "-profile:v",
        "main",
        "-pix_fmt",
        "yuv420p",
        "-b:v",
        str(settings.video_bitrate),
        "-threads",
        "1",
        "-flags:v",
        "+bitexact",
        "-c:a",
        "aac",
        "-ac",
        "1",
        "-ar",
        str(settings.audio_sample_rate),
        "-b:a",
        str(settings.audio_bitrate),
        "-flags:a",
        "+bitexact",
        "-c:s",
        "mov_text",
        # Sparse captions must not trigger timing-dependent queue flushes.
        # These are output format options; the earlier fflags apply to input.
        "-fflags",
        "+bitexact",
        "-max_interleave_delta",
        "0",
        "-movflags",
        "+faststart",
        "-metadata",
        f"creation_time={datetime.fromtimestamp(epoch, UTC).isoformat()}",
    ]
    for index, (_, language) in enumerate(audio_languages):
        command += [
            f"-metadata:s:a:{index}",
            f"language={codes[language]}",
            f"-metadata:s:a:{index}",
            f"title={names[language]} (original audio)",
            f"-disposition:a:{index}",
            "default" if index == 0 else "0",
        ]
    for index, track in enumerate(subtitles):
        command += [
            f"-metadata:s:s:{index}",
            f"language={codes[track.language]}",
            f"-metadata:s:s:{index}",
            f"title={names[track.language]}",
            f"-disposition:s:{index}",
            "0",
        ]
    subprocess.run([*command, str(target)], check=True, capture_output=True)
    output = probe(target)
    validate_video(output, clip, settings, codes, order)
    check_faststart(target)
    if abs(source_end - float(output["format"]["duration"])) > 0.15:
        raise ValueError(
            f"Normalized video duration changed: {source_end} to "
            f"{output['format']['duration']} seconds"
        )
    return {
        "source": source,
        "source_media_end_seconds": source_end,
        "subtitles": caption_audits,
        "output": output,
    }


def build_video(
    root: Path,
    config: Configuration,
    catalog: dict[str, Item],
    cache: Path,
    output: Path,
    identifier: str,
    epoch: int,
) -> dict:
    if output.exists():
        raise ValueError("Video output must be new")
    settings = VideoSettings.model_validate(read_yaml(root / "pipelines/video/settings.yaml"))
    clips = read_yaml(root / "pipelines/video/clips.yaml")
    clip = Clip.model_validate(clips[identifier])
    item = catalog[clip.source_id]
    if not video_rights_allowed(item):
        raise ValueError("Video needs confirmed per-item federal or Commons redistribution rights")
    inputs = {
        clip.source_id,
        settings.language_codes_id,
        *(track.source_id for track in clip.subtitles),
    }
    for track in clip.subtitles:
        caption = catalog[track.source_id]
        if caption.license not in {
            "US-PD",
            "CC0-1.0",
            "CC-BY-3.0",
            "CC-BY-4.0",
            "CC-BY-SA-4.0",
            "CC-BY-SA-3.0",
        } or not caption.license_proof_url.startswith("https://"):
            raise ValueError("Every subtitle input needs confirmed redistribution rights")
    paths = {key: cached_input(catalog[key], cache) for key in sorted(inputs)}
    codes = language_codes(paths[settings.language_codes_id], config)
    names = {edition.code: edition.name for edition in config.languages}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-video-") as temporary:
        stage = Path(temporary)
        files = stage / "files"
        files.mkdir()
        audit = normalize(clip, paths, files / clip.filename, settings, codes, names, epoch)
        (stage / "audit.json").write_text(json.dumps(audit, sort_keys=True, indent=2) + "\n")
        sources = [catalog[key] for key in sorted(inputs - {settings.language_codes_id})]
        (files / (Path(clip.filename).stem + "_SOURCE.TXT")).write_text(
            "\n\n".join(
                f"{entry.title}\n{entry.url}\nSHA-256: {entry.sha256}\n{entry.attribution}\n"
                f"{entry.license}: {entry.license_proof_url}"
                for entry in sources
            )
            + "\n\nNormalized picture and audio; subtitles remain separate tracks. "
            "No text overlay added.\n"
        )
        if (urlparse(item.url or "").hostname or "").endswith("cdc.gov"):
            with (files / (Path(clip.filename).stem + "_SOURCE.TXT")).open("a") as attribution:
                attribution.write(
                    "\nSource: CDC. Use of this material does not imply endorsement of "
                    "Common Knowledge "
                    "by CDC, HHS or the United States Government. The original material is "
                    "available without charge on the CDC website linked above.\n"
                )
        recipe = hashlib.sha256()
        for name in (
            "src/ck/video.py",
            "src/ck/generated.py",
            "pipelines/video/settings.yaml",
            "pipelines/video/clips.yaml",
            "config/languages.yaml",
            "Dockerfile.build",
        ):
            recipe.update(name.encode() + b"\0" + (root / name).read_bytes())
        result = generation_manifest(
            stage,
            "video-v1-" + recipe.hexdigest(),
            {key: catalog[key].sha256 for key in sorted(inputs)},
            complete=True,
            epoch=epoch,
            intermediates=["audit.json"],
            tool_versions=Path("/opt/ck-tool-versions.txt").read_text(),
        )
        stage.rename(output)
    return result
