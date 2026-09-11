"""Archive experimental reading samples without claiming release acceptance."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

from artifact_utils import sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.build / "manifest.json").read_text())
    report = json.loads((args.build / "pilot-report.json").read_text())
    for name in ("english.zip", "chinese.zip"):
        if sha(args.build / name) != report["package_sha256"][name]:
            raise ValueError("Report does not belong to these packages")
    if manifest["status"] != "candidate" or not report["semantic_checks_passed"]:
        raise ValueError("Need a clean, locked build with passed selected fact checks")
    args.destination.mkdir(parents=True, exist_ok=False)
    for case in ("populated", "partial"):
        for language in ("english", "chinese"):
            for extension in ("pdf", "docx"):
                filename = f"{case}-{language}.{extension}"
                shutil.copyfile(args.build / "renders" / filename, args.destination / filename)
    for filename in ("manifest.json", "pilot-report.json", "render-results.json", "translation-audit.json", "structure-audit.json", "readability-checks.json"):
        shutil.copyfile(args.build / filename, args.destination / filename)
    if (args.build / "word-preview").exists():
        shutil.copytree(args.build / "word-preview", args.destination / "word-preview")
    runtime = subprocess.check_output([
        "docker", "inspect", "--format", "{{.Name}} {{.Config.Image}} {{.Image}}",
        "science-europe-pilot-server-1", "science-europe-pilot-docworker-1",
    ], text=True)
    (args.destination / "runtime-images.txt").write_text(runtime)
    (args.destination / "checksums.json").write_text(json.dumps({
        str(path.relative_to(args.destination)): sha(path)
        for path in sorted(args.destination.rglob("*")) if path.is_file()
    }, indent=2) + "\n")
    print(args.destination)


if __name__ == "__main__":
    main()
