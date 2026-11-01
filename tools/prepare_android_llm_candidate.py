"""Render a proposed Android companion from a verified frozen LLM bundle.

Writes a separate review directory. It never regenerates or modifies the frozen
bundle, selected settings, third-party APK, or publisher source files.
"""

import argparse
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ck.catalog import load_catalog
from ck.config import LocalLLM, read_yaml
from ck.generated import verified_generated_files
from ck.llm import android_prompt_settings, system_prompt

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--root", type=Path, default=Path.cwd())
parser.add_argument("--bundle", type=Path, required=True)
parser.add_argument("--bundle-id", choices=["local_llm_sample", "local_llm_full"], required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
    raise ValueError("Android companion review output must be new")
catalog = load_catalog(args.root)
_, files = verified_generated_files(catalog[args.bundle_id], args.bundle, catalog)
proposal = read_yaml(args.root / "pipelines/android_llm_candidate/settings.yaml")
baseline = LocalLLM.model_validate(read_yaml(args.root / proposal["baseline_settings"]))
settings = android_prompt_settings(baseline)
args.output.mkdir(parents=True)
grounding = {}
for language in ("en", "es"):
    source = files[f"ui/start-{language}.txt"].read_text()
    prompt, grounding[language] = system_prompt(
        args.root, settings, language, source, section_index_only=True
    )
    (args.output / f"system-{language}.txt").write_text(prompt)
environment = Environment(
    loader=FileSystemLoader(args.root / "pipelines/android_llm_candidate"),
    autoescape=False,
    undefined=StrictUndefined,
)
(args.output / "HOW_TO_ANDROID.md").write_text(
    environment.get_template("how-to.md.j2").render(settings=settings)
)
(args.output / "proposal.json").write_text(
    json.dumps(
        {
            "candidate_apk": settings.android.apk_id,
            "context_tokens": settings.context_tokens,
            "source_bundle_id": args.bundle_id,
            "source_bundle_sha256": catalog[args.bundle_id].sha256,
            "grounding": grounding,
            "selection_or_release_approval": False,
            "original_bundle_modified": False,
        },
        sort_keys=True,
        indent=2,
    )
    + "\n"
)
print(json.dumps({"candidate": settings.android.apk_id, "grounding": grounding}))
