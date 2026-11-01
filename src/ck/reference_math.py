"""Render publisher MathML with a pinned, offline vector renderer."""

import hashlib
import json
import subprocess
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path, PurePosixPath

from ck.config import Identifier, Model, read_yaml
from ck.generated import cached_input


class Settings(Model):
    source_id: Identifier


def math_source_id(root: Path) -> str:
    return Settings.model_validate(read_yaml(root / "pipelines/math/settings.yaml")).source_id


def validate_svg(svg: str) -> None:
    root = ET.fromstring(svg)
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError("Math renderer did not return an SVG")
    allowed = {
        "svg",
        "g",
        "path",
        "rect",
        "line",
        "polygon",
        "polyline",
        "circle",
        "ellipse",
        "defs",
        "use",
        "title",
        "desc",
    }
    for node in root.iter():
        name = node.tag.rsplit("}", 1)[-1]
        empty_alignment = (
            name == "text"
            and node.get("data-id-align") == "true"
            and not "".join(node.itertext()).strip()
        )
        if (name not in allowed and not empty_alignment) or node.get("data-mml-node") == "merror":
            raise ValueError(f"Unsupported or failed equation output: {name}")
        for key, value in node.attrib.items():
            key = key.rsplit("}", 1)[-1].lower()
            if key.startswith("on") or "url(" in value.lower():
                raise ValueError("Equation SVG contains active or external content")
            if key in {"href", "src"} and not value.startswith("#"):
                raise ValueError("Equation SVG contains an external resource")


def extract_package(archive: Path, output: Path) -> None:
    with tarfile.open(archive, "r:gz") as source:
        for member in source.getmembers():
            path = PurePosixPath(member.name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or not path.parts
                or path.parts[0] != "package"
                or not (member.isdir() or member.isfile())
            ):
                raise ValueError("Unsafe math renderer archive member")
        source.extractall(output, filter="data")


class MathRenderer:
    def __init__(self, root: Path, catalog: dict, cache: Path):
        self.root, self.catalog, self.cache = root, catalog, cache
        self.temporary = None
        self.process = None
        self.errors = None
        self.versions = ""
        self.notice = ""

    def __enter__(self):
        try:
            item = self.catalog[math_source_id(self.root)]
            if item.license != "Apache-2.0" or item.family != "binaries":
                raise ValueError("Math renderer package license or type is unconfirmed")
            archive = cached_input(item, self.cache)
            self.temporary = tempfile.TemporaryDirectory(prefix="ck-math-")
            directory = Path(self.temporary.name)
            extract_package(archive, directory)
            package = directory / "package"
            metadata = json.loads((package / "package.json").read_text())
            if metadata["version"] != item.version:
                raise ValueError("Math renderer package version differs from its catalog pin")
            self.notice = (
                f"{item.title}, {item.version}\n{item.attribution}\n"
                f"{item.license}: {item.license_proof_url}\n"
                "Used to render source equations during PDF generation.\n\n"
                + (package / "LICENSE").read_text()
            )
            bun = subprocess.run(
                ["bun", "--version"], text=True, capture_output=True, check=True
            ).stdout.strip()
            self.versions = f"\nBun: {bun}\nMathJax: {item.version} ({item.sha256})"
            self.errors = tempfile.TemporaryFile(mode="w+t")
            self.process = subprocess.Popen(
                ["bun", "run", str(self.root / "pipelines/math/render.mjs"), str(package)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self.errors,
                text=True,
            )
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __call__(self, mathml: str) -> str:
        self.process.stdin.write(json.dumps({"mathml": mathml}) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            self.errors.seek(0)
            raise ValueError("Math renderer failed: " + self.errors.read()[-1000:])
        response = json.loads(line)
        if response.get("error"):
            raise ValueError("Source equation failed to render: " + response["error"])
        svg = response["svg"]
        validate_svg(svg)
        return svg

    def __exit__(self, *args):
        if self.process:
            try:
                self.process.stdin.close()
            except BrokenPipeError:
                pass
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process.stdout.close()
        if self.errors:
            self.errors.close()
        if self.temporary:
            self.temporary.cleanup()


def prepare_equations(document, content, renderer) -> list[dict]:
    result = []
    nodes = content.find_all(lambda node: node.name == "math" or node.name.endswith(":math"))
    for number, node in enumerate(list(nodes), 1):
        if node.name != "math":
            raise ValueError("Unsupported prefixed MathML namespace")
        if node.find_parent("math") is not None:
            continue
        if node.find_parent(["svg", "script", "style", "form", "object", "iframe"]):
            continue
        if renderer is None:
            raise ValueError("Source MathML needs the verified offline equation renderer")
        raw = str(node)
        svg = renderer(raw)
        alternate = node.get("alttext")
        annotation = node.find("annotation", attrs={"encoding": "application/x-tex"})
        if not alternate and annotation is not None:
            alternate = annotation.get_text()
        if alternate:
            svg = svg.replace(
                "<svg ", '<svg aria-label="' + escape(alternate, quote=True) + '" ', 1
            )
        validate_svg(svg)
        removed_fallbacks = 0
        group = node.find_parent(class_="mwe-math-element")
        if group is not None and len(group.find_all("math")) == 1:
            for fallback in list(
                group.select(
                    "img.mwe-math-fallback-image-inline, img.mwe-math-fallback-image-display"
                )
            ):
                fallback.decompose()
                removed_fallbacks += 1
        identity = hashlib.sha256(raw.encode()).hexdigest()
        placeholder = document.new_tag("span", attrs={"class": f"ck-equation-{number}-{identity}"})
        if node.get("id"):
            placeholder["id"] = node["id"]
        placeholder.string = "Source equation"
        node.replace_with(placeholder)
        result.append(
            {
                "placeholder": placeholder,
                "svg": svg,
                "source_mathml_sha256": identity,
                "svg_sha256": hashlib.sha256(svg.encode()).hexdigest(),
                "replaced_math_fallbacks": removed_fallbacks,
            }
        )
    return result


def restore_equations(html: str, equations: list[dict]) -> tuple[str, list[dict]]:
    audit = []
    for equation in equations:
        placeholder = str(equation["placeholder"])
        if html.count(placeholder) != 1:
            raise ValueError("Source equation placeholder was lost or duplicated")
        identifier = equation["placeholder"].get("id")
        anchor = f' id="{escape(identifier, quote=True)}"' if identifier else ""
        html = html.replace(
            placeholder,
            '<span class="source-equation"' + anchor + ">" + equation["svg"] + "</span>",
        )
        audit.append(
            {
                key: equation[key]
                for key in ("source_mathml_sha256", "svg_sha256", "replaced_math_fallbacks")
            }
        )
    return html, audit
