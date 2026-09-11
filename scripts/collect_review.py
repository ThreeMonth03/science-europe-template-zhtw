"""Collect explicitly experimental review evidence; never stage a release."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from artifact_utils import sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--revision-build", type=Path, required=True)
    parser.add_argument("--upgrade", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    base = json.loads((args.build / "manifest.json").read_text())
    revision = json.loads((args.revision_build / "manifest.json").read_text())
    assert base["source"] == revision["source"]
    assert base["translation"]["version"] != revision["translation"]["version"]
    assert sha(args.build / "english.zip") == sha(args.revision_build / "english.zip")
    assert sha(args.build / "chinese.zip") != sha(args.revision_build / "chinese.zip")
    args.destination.mkdir(parents=True, exist_ok=False)
    copied = []
    for case in ("populated", "partial"):
        for language in ("english", "chinese"):
            for extension in ("pdf", "docx"):
                name = f"{case}-{language}.{extension}"
                shutil.copyfile(args.build / "renders" / name, args.destination / name)
                copied.append(name)
    for filename in (
        "manifest.json",
        "pilot-report.json",
        "render-results.json",
        "translation-audit.json",
        "structure-audit.json",
    ):
        shutil.copyfile(args.build / filename, args.destination / filename)
        copied.append(filename)
    shutil.copyfile(args.upgrade / "report.json", args.destination / "upgrade-replay.json")
    version_report = {
        "source_unchanged": True,
        "english_package_identical": True,
        "source": base["source"],
        "source_checkouts": base["checkouts"],
        "translation_versions": [
            base["translation"]["version"],
            revision["translation"]["version"],
        ],
        "sha256": {
            "english.zip": sha(args.build / "english.zip"),
            "chinese-base.zip": sha(args.build / "chinese.zip"),
            "chinese-revision.zip": sha(args.revision_build / "chinese.zip"),
        },
    }
    (args.destination / "version-rehearsal.json").write_text(
        json.dumps(version_report, indent=2) + "\n"
    )
    runtime = subprocess.check_output(
        [
            "docker",
            "inspect",
            "--format",
            "{{.Name}} {{.Config.Image}} {{.Image}}",
            "science-europe-pilot-server-1",
            "science-europe-pilot-docworker-1",
        ],
        text=True,
    )
    (args.destination / "runtime-images.txt").write_text(runtime)
    (args.destination / "checksums.json").write_text(
        json.dumps({name: sha(args.destination / name) for name in copied}, indent=2) + "\n"
    )
    print(args.destination)


if __name__ == "__main__":
    main()
