#!/usr/bin/env python3
"""Render the CV PDF from _data/cv.yml with RenderCV.

_data/cv.yml also feeds the CV web page, which uses two fields RenderCV rejects:
`label` (the job title) and `summary` (the profile paragraph). This writes a
RenderCV-compatible copy (label -> headline, summary -> a "Profile" section,
languages -> one-line "German: Native" entries), renders it with the design,
locale and settings files in assets/rendercv/, then removes the copy and
everything in the output folder except the PDF (Typst source, copied photo).

Usage: python bin/render_cv.py   (needs `pip install -r requirements.txt`)
"""

import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "_data" / "cv.yml"
# Next to the source so the relative paths in settings.yaml still resolve.
# The leading dot keeps Jekyll from loading it as site data.
COPY = SOURCE.with_name(".cv.rendercv.yml")
CONFIG = ROOT / "assets" / "rendercv"
OUTPUT = CONFIG / "rendercv_output"


def main() -> int:
    data = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    cv = data["cv"]
    if "label" in cv:
        cv["headline"] = cv.pop("label")
    summary = cv.pop("summary", None)
    if summary:
        cv["sections"] = {"Profile": [summary], **cv.get("sections", {})}
    languages = cv.get("sections", {}).get("Languages")
    if languages:
        cv["sections"]["Languages"] = [{"label": entry["name"], "details": entry["summary"]} for entry in languages]
    COPY.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    # RenderCV ignores the design/locale paths inside settings.yaml, so pass them explicitly.
    command = [
        "rendercv", "render", str(COPY),
        "--settings", str(CONFIG / "settings.yaml"),
        "--design", str(CONFIG / "design.yaml"),
        "--locale-catalog", str(CONFIG / "locale.yaml"),
    ]
    try:
        result = subprocess.run(command, cwd=ROOT)
    finally:
        COPY.unlink(missing_ok=True)
    for leftover in OUTPUT.iterdir():
        if leftover.is_file() and leftover.suffix != ".pdf":
            leftover.unlink()
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
