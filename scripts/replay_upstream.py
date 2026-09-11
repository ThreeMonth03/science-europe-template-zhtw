"""Replay a real upstream patch upgrade without changing the custom branch."""

import argparse
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import asdict
from pathlib import Path

from dsw_document_template_tool.template_transform import expand_template_dir
from dsw_document_template_tool.translation_tree import (
    audit_translation_tree,
    export_translation_tree,
    merge_translation_tree,
)

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--english", type=Path, required=True)
    parser.add_argument("--tooling", type=Path, required=True)
    parser.add_argument("--old-tree", type=Path, required=True)
    args = parser.parse_args()
    english, tooling = args.english.resolve(), args.tooling.resolve()
    output = Path(tempfile.mkdtemp(prefix="upgrade-", dir=ROOT / "outputs"))
    report = {"replay_only": True, "upstream": {}, "source_tree": str(args.old_tree.resolve())}
    for version in ("1.30.0", "1.30.1"):
        folder = output / version
        folder.mkdir()
        archive = subprocess.check_output(
            ["git", "-C", str(english), "archive", f"upstream/v{version}"]
        )
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(folder / "source", filter="data")
        commit = subprocess.check_output(
            ["git", "-C", str(english), "rev-parse", f"upstream/v{version}"], text=True
        ).strip()
        expand_template_dir(source_dir=folder / "source", output_dir=folder / "expanded")
        export_translation_tree(
            source_dir=folder / "expanded",
            output_dir=folder / "tree",
            source_lang="en",
            target_lang="zh_Hant",
        )
        old = args.old_tree if version == "1.30.0" else output / "1.30.0/merged"
        migration = merge_translation_tree(
            old_tree_dir=old,
            new_tree_dir=folder / "tree",
            output_dir=folder / "merged",
            source_lang="en",
            target_lang="zh_Hant",
        )
        issues = audit_translation_tree(tree_dir=folder / "merged", source_dir=folder / "expanded")
        report["upstream"][version] = {
            "commit": commit,
            "migration": asdict(migration),
            "audit_issues": [asdict(issue) for issue in issues],
        }
        result = subprocess.run(
            [
                str(tooling / ".venv/bin/dsw-tdk"),
                "--no-config",
                "package",
                str(folder / "source"),
                "--output",
                str(folder / "english.zip"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        (folder / "package.log").write_text(result.stdout + result.stderr)
        for case in ("empty", "populated"):
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/render.py"),
                    "--build",
                    str(folder),
                    "--project",
                    str(english / f"fixtures/pilot/en/{case}.json"),
                    "--language",
                    "english",
                    "--format",
                    "html",
                    "--name",
                    case,
                    "--tooling",
                    str(tooling),
                ],
                text=True,
                capture_output=True,
            )
            (folder / f"render-{case}.log").write_text(result.stdout + result.stderr)
            report["upstream"][version][f"{case}_render_passed"] = result.returncode == 0
    (output / "upstream.diff").write_bytes(
        subprocess.check_output(
            ["git", "-C", str(english), "diff", "upstream/v1.30.0", "upstream/v1.30.1", "--"]
        )
    )
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(output)


if __name__ == "__main__":
    main()
