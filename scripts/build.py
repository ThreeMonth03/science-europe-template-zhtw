"""Build a traceable bilingual candidate using the existing translation pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import yaml
import dsw_document_template_tool

from artifact_utils import canonicalize_zip

from dsw_document_template_tool.template_transform import expand_template_dir
from dsw_document_template_tool.translation_tree import (
    audit_translated_template_structure,
    audit_translation_tree,
    export_translation_tree,
    merge_translation_tree,
    sync_translation_tree,
)
from dsw_document_template_tool._translation_tree.document import parse_translation_document
from dsw_document_template_tool._translation_tree.manifest import load_tree_manifest

ROOT = Path(__file__).resolve().parents[1]


def git(path: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), *arguments], text=True, stderr=subprocess.PIPE
    ).strip()


def fingerprint(path: Path) -> dict:
    try:
        commit = git(path, "rev-parse", "HEAD")
    except subprocess.CalledProcessError:
        commit = None
    return {"commit": commit, "dirty": bool(git(path, "status", "--porcelain"))}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require_clean_lock(path: Path, lock: str, preview: bool) -> dict:
    state = fingerprint(path)
    if not preview and (state["dirty"] or state["commit"] != lock):
        raise ValueError(f"Clean checkout of locked commit required: {path}")
    return state


PACKAGE_INPUT_PATHS = ('template.json', 'src', 'scripts/prepare_layout.py', 'PACKAGE_README.md', 'LICENSE')


def package_readme(root: Path) -> Path:
    path = root / 'PACKAGE_README.md'
    if not path.is_file() or not path.read_text().strip():
        raise ValueError(f'Non-empty package README required: {path}')
    return path


def package_timestamp(english: Path) -> str:
    # Navigation docs, tests and review archives are not package inputs.
    value = git(english, 'log', '-1', '--format=%cI', 'HEAD', '--', *PACKAGE_INPUT_PATHS)
    if not value:
        raise ValueError('No committed English package inputs found')
    return datetime.fromisoformat(value).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def build(args) -> Path:
    config = yaml.safe_load((ROOT / "pipeline.yml").read_text())
    if args.translation_version is not None:
        if not args.preview:
            raise ValueError(
                "Version override is a preview-only rehearsal; edit and commit pipeline.yml for a candidate"
            )
        config["translation"]["version"] = args.translation_version
    english, tooling = args.english.resolve(), args.tooling.resolve()
    if not Path(dsw_document_template_tool.__file__).resolve().is_relative_to(tooling / "src"):
        raise ValueError(
            "The imported conversion tool does not come from --tooling; install that checkout in editable mode"
        )
    states = {
        "english": require_clean_lock(english, config["source"]["commit"], args.preview),
        "tooling": require_clean_lock(tooling, config["tooling"]["commit"], args.preview),
        "translation": fingerprint(ROOT),
    }
    if not args.preview and states["translation"]["dirty"]:
        raise ValueError("Release candidates require committed translations and configuration")
    if not args.preview and args.refresh:
        raise ValueError(
            "Refresh translations in a preview, review and commit them before a candidate build"
        )
    output_root = ROOT / "outputs"
    output_root.mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="build-", dir=output_root))
    tdk = tooling / ".venv/bin/dsw-tdk"
    font = tooling / "src/dsw_document_template_tool/resources/fonts/NotoSansTC-Variable.ttf"
    timestamp = package_timestamp(english)
    for language in ("en", "zh-Hant"):
        prepared = output / language
        prepared.mkdir()
        shutil.copytree(english / "src", prepared / "src")
        for filename in ("template.json", "LICENSE"):
            shutil.copyfile(english / filename, prepared / filename)
        shutil.copyfile(package_readme(english), prepared / 'README.md')
        metadata = json.loads((prepared / "template.json").read_text())
        for key, config_key in (
            ("organizationId", "organization_id"),
            ("templateId", "template_id"),
            ("version", "version"),
        ):
            if metadata[key] != str(config["source"][config_key]):
                raise ValueError(f"Source metadata differs from pipeline lock: {key}")
        subprocess.run(
            [
                sys.executable,
                str(english / "scripts/prepare_layout.py"),
                "--template",
                str(prepared),
                "--font",
                str(font),
                "--language",
                language,
            ],
            check=True,
        )
        for license_file in font.parent.glob("*.txt"):
            shutil.copyfile(license_file, prepared / "src/fonts" / license_file.name)
    expanded = output / "expanded"
    expand_template_dir(
        source_dir=output / "zh-Hant",
        output_dir=expanded,
        profile=config["tooling"]["profile"],
        exclude_profile_paths=tuple(config["tooling"]["exclude_profile_paths"]),
    )
    fresh = output / "fresh-translation"
    export_translation_tree(
        source_dir=expanded, output_dir=fresh, source_lang="en", target_lang="zh_Hant"
    )
    tree = ROOT / "translation"
    if args.refresh:
        old_tree = tree if tree.exists() else args.seed_tree
        if old_tree is not None:
            report = merge_translation_tree(
                old_tree_dir=old_tree,
                new_tree_dir=fresh,
                output_dir=output / "merged",
                source_lang="en",
                target_lang="zh_Hant",
            )
            write_json(output / "migration.json", asdict(report))
            fresh = output / "merged"
        # Keep historical translations in Git; do not remove unrelated files.
        if tree.exists():
            shutil.move(str(tree), output / "previous-translation")
        shutil.copytree(fresh, tree)
    if not tree.exists():
        raise ValueError("No translation tree; use --refresh to initialize it")
    issues = audit_translation_tree(tree_dir=tree, source_dir=expanded)
    write_json(output / "translation-audit.json", [asdict(i) for i in issues])
    if issues:
        raise ValueError(f"Translation audit failed: {output / 'translation-audit.json'}")
    target = config["translation"]
    translated = output / "translated"
    sync_translation_tree(
        tree_dir=tree,
        source_dir=expanded,
        output_dir=translated,
        source_lang="en",
        target_lang="zh_Hant",
        template_organization_id=target["organization_id"],
        template_id=target["template_id"],
        template_name=target["name"],
        template_version=str(target["version"]),
        public_readme_path=package_readme(ROOT),
    )
    issues = audit_translated_template_structure(source_dir=expanded, output_dir=translated)
    write_json(output / "structure-audit.json", [asdict(i) for i in issues])
    if issues:
        raise ValueError(f"Structure audit failed: {output / 'structure-audit.json'}")
    units = load_tree_manifest(tree)["units"]
    blanks = [
        u["document_path"]
        for u in units
        if not parse_translation_document(
            document_path=tree / u["document_path"], source_lang="en", target_lang="zh_Hant"
        ).strip()
    ]
    if blanks and not args.preview:
        raise ValueError(f"Release candidate has {len(blanks)} untranslated units")
    for name, directory in (("english", output / "en"), ("chinese", translated)):
        for operation in (
            [str(tdk), "verify", str(directory)],
            [str(tdk), "package", str(directory), "--output", str(output / f"{name}.zip")],
        ):
            result = subprocess.run(operation, check=True, capture_output=True, text=True)
            with (output / f"{name}-build.log").open("a") as log:
                log.write(result.stdout + result.stderr)
        canonicalize_zip(output / f"{name}.zip", timestamp)
    hashes = {
        str(p.relative_to(output)): sha(p)
        for p in sorted(output.rglob("*"))
        if p.is_file() and (p.suffix in (".zip", ".docx", ".css") or p.name == "template.json")
    }
    write_json(
        output / "manifest.json",
        {
            "status": "preview" if args.preview else "candidate",
            "source": config["source"],
            "translation": config["translation"],
            "runtime": config["runtime"],
            "package_timestamp": timestamp,
            "package_readme_sha256": {'english': sha(package_readme(english)), 'chinese': sha(package_readme(ROOT))},
            "checkouts": states,
            "translation_units": len(units),
            "untranslated_units": blanks,
            "sha256": hashes,
            "translation_tree_sha256": {
                str(p.relative_to(tree)): sha(p) for p in sorted(tree.rglob("translation.md"))
            },
        },
    )
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--english", type=Path, required=True)
    parser.add_argument("--tooling", type=Path, required=True)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--seed-tree", type=Path)
    parser.add_argument("--translation-version", help="Preview-only independent version rehearsal")
    args = parser.parse_args()
    print(build(args))
