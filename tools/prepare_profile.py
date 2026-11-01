"""Dispatch input pipelines through pinned containers; never execute build tools on the host."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path


class Driver:
    def __init__(self, root, work, cache, generated, build_image, atlas_image):
        self.root, self.work, self.cache, self.generated = map(
            lambda path: Path(path).resolve(), (root, work, cache, generated)
        )
        for directory in (self.work, self.cache, self.generated):
            directory.mkdir(parents=True, exist_ok=True)
        self.images = {}
        for name, image in (("build", build_image), ("atlas", atlas_image)):
            self.images[name] = subprocess.check_output(
                ["docker", "image", "inspect", "--format", "{{.Id}}", image], text=True
            ).strip()
        self.epoch = None
        self.produced = set()

    def run(self, args, *, native=False, network=False, entrypoint=None):
        command = ["docker", "run", "--rm", "--platform", "linux/amd64"]
        if not network:
            command += ["--network=none"]
        command += [
            "--volume",
            str(self.root) + ":/source:ro",
            "--volume",
            str(self.work) + ":/work",
            "--volume",
            str(self.cache) + (":/cache" if network else ":/cache:ro"),
            "--volume",
            str(self.generated) + ":/generated",
            "--workdir",
            "/workspace/pipelines/atlas" if native else "/source",
            "--env",
            "PYTHONPATH=/source/src",
            "--entrypoint",
            entrypoint or ("bun" if native else "/workspace/.venv/bin/ck"),
            self.images["atlas" if native else "build"],
            *map(str, args),
        ]
        subprocess.run(command, check=True)

    def ck(self, *arguments, epoch=False, network=False):
        self.run([*arguments, *(["--epoch", str(self.epoch)] if epoch else [])], network=network)

    def path(self, value):
        for prefix, directory in (("/work/", self.work), ("/generated/", self.generated)):
            if value.startswith(prefix):
                path = directory / value.removeprefix(prefix)
                if not path.resolve().is_relative_to(directory):
                    break
                return path
        raise ValueError("Workflow path escapes its output mounts")

    def jobs(self, folder, national):
        directory = self.path(folder)
        paths = sorted(directory.glob("*/jobs.json")) if national else [directory / "jobs.json"]
        if not paths or any(not path.is_file() or path.is_symlink() for path in paths):
            raise ValueError("Atlas preparation produced no complete jobs")
        return [folder + "/" + path.relative_to(directory).as_posix() for path in paths]

    def action(self, action):
        kind = action["kind"]
        if kind == "ck":
            self.ck(*action["args"], epoch=True)
        elif kind == "extract":
            self.run(
                [
                    "/source/tools/extract_atlas.py",
                    "--root",
                    "/source",
                    "--jobs",
                    *self.jobs(action["jobs"], action["national"]),
                    "--source-file",
                    "/cache/" + action["planet_sha256"],
                    "--output",
                    action["output"],
                ],
                native=True,
                entrypoint="python3",
            )
        elif kind == "render-compose":
            for job in self.jobs(action["jobs"], action["national"]):
                self.run(["run", "render", job], native=True)
                output = action["output"]
                if action["national"]:
                    output += "/" + self.path(job).parent.name
                self.ck("atlas", "compose", "--jobs", job, "--output", output)
        elif kind == "collect":
            folders = sorted(
                path for path in self.path(action["folder"]).iterdir() if path.is_dir()
            )
            if not folders:
                raise ValueError("No completed state folders to collect")
            self.ck(
                *action["command"],
                *action["args"],
                "--outputs",
                *[action["folder"] + "/" + path.name for path in folders],
                "--output",
                action["output"],
                epoch=True,
            )
        elif kind == "phrasebooks":
            self.ck("phrasebooks", "--cache", "/cache", "--output", action["output"], epoch=True)
            for directory in sorted(self.path(action["output"]).iterdir()):
                identifier = "phrasebook_" + directory.name.lower().replace("-", "_")
                target = self.generated / identifier
                if target.exists():
                    raise ValueError("Phrasebook publication would overwrite an existing input")
                shutil.copytree(directory, target)
                self.produced.add(identifier)
        else:
            raise ValueError("Unknown input workflow action: " + kind)

    def prepare(self, profile, epoch=None, variants=None):
        selection = ["--variants", *map(str, variants)] if variants is not None else []
        self.ck("check-profile", "--profile", profile, *selection)
        args = ["prepare-plan", "--profile", profile, "--output", "/work/plan.json"]
        args += selection
        if epoch is not None:
            args += ["--epoch", str(epoch)]
        self.ck(*args)
        plan = json.loads((self.work / "plan.json").read_text())
        self.epoch = plan["source_date_epoch"]
        if any((self.generated / task["id"]).exists() for task in plan["tasks"]):
            raise ValueError("Use a fresh GENERATED_DIR; refusing to reuse generated inputs")
        commit = subprocess.check_output(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True
        ).strip()
        dirty = subprocess.check_output(
            ["git", "-C", str(self.root), "status", "--porcelain"], text=True
        )
        if profile == "full":
            tag = subprocess.check_output(
                ["git", "-C", str(self.root), "describe", "--exact-match", "--tags", "HEAD"],
                text=True,
            ).strip()
            if dirty or tag != "v" + plan["version"]:
                raise ValueError("Full input preparation requires the clean matching release tag")
        core = self.work / "core-for-plan"
        if core.exists():
            raise ValueError("Choose a new workflow directory for a clean preparation run")
        self.ck("core", "--profile", profile, "--output", "/work/core-for-plan", epoch=True)
        self.ck(*args, "--core", "/work/core-for-plan")
        plan = json.loads((self.work / "plan.json").read_text())
        if plan["capacity_assumed"]:
            raise ValueError("A capacity inspection assumption cannot execute a build")
        for offset in range(0, len(plan["downloads"]), 100):
            self.ck(
                "fetch-build-inputs",
                *plan["downloads"][offset : offset + 100],
                "--cache",
                "/cache",
                network=True,
            )
        phrasebooks_done = False
        for task in plan["tasks"]:
            existing = self.generated / task["id"]
            if existing.exists():
                if task["id"] not in self.produced:
                    raise ValueError(
                        "Use a fresh GENERATED_DIR; refusing to reuse generated inputs"
                    )
                self.ck("verify-prepared", task["id"], "--generated", "/generated", epoch=True)
                continue
            for action in task["actions"]:
                if action["kind"] == "phrasebooks":
                    if phrasebooks_done:
                        continue
                    phrasebooks_done = True
                self.action(action)
            self.ck("verify-prepared", task["id"], "--generated", "/generated", epoch=True)
        receipt = {
            "profile": profile,
            "variants": plan["variants"],
            "source_date_epoch": self.epoch,
            "images": self.images,
            "selected": plan["selected"],
            "complete": True,
            "commit": commit,
            "source_dirty": bool(dirty),
        }
        (self.work / "preparation.json").write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--profile", choices=["dev", "sample", "full"], required=True)
    parser.add_argument("--variants", type=int, nargs="+", choices=range(1, 9))
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--build-image", required=True)
    parser.add_argument("--atlas-image", required=True)
    parser.add_argument("--epoch", type=int)
    args = parser.parse_args()
    Driver(
        args.root, args.work, args.cache, args.generated, args.build_image, args.atlas_image
    ).prepare(args.profile, args.epoch, args.variants)


if __name__ == "__main__":
    main()
