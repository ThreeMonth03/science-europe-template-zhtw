"""Build a shared English DT, authoritative Chinese PO, and generated 4.34 DT."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import yaml
import dsw_document_template_tool

from artifact_utils import PO_ARTIFACTS, PO_PROFILE, canonicalize_zip

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


def localize_format_names(metadata: dict, names: dict) -> None:
    """Display labels only: never change format identities or rendering steps."""
    formats = metadata['formats']
    identifiers = [item['uuid'] for item in formats]
    if len(set(identifiers)) != len(identifiers) or not set(names) <= set(identifiers):
        raise ValueError('Format labels must name unique existing format UUIDs')
    if any(not isinstance(label, str) or not label.strip() for label in names.values()):
        raise ValueError('Format labels must be non-empty text')
    for item in formats:
        if item['uuid'] in names:
            item['name'] = names[item['uuid']]


def set_template_language(metadata: dict, language: str) -> None:
    """Declare the descriptor locale without changing format identities or steps."""
    if language not in ('en', 'zh-Hant'):
        raise ValueError('Unsupported template language')
    metadata['language'] = language


def select_tdk(tooling: Path, override: Path | None = None) -> Path:
    """Use the active locked build environment; tooling code is pinned separately."""
    return (override if override is not None else Path(sys.executable).with_name('dsw-tdk')).resolve()


def tdk_provenance(executable: Path) -> dict:
    output = subprocess.check_output([str(executable), '--version'], text=True).strip()
    match = re.search(r'\bversion\s+(\S+)\s*$', output)
    if match is None:
        raise ValueError(f'Cannot identify TDK version: {executable}')
    return {'executable': str(executable), 'version': match.group(1)}


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
    # A shallow boundary treats a tests-only commit as adding the whole tree,
    # silently changing package metadata even when every source byte matches.
    if git(english, 'rev-parse', '--is-shallow-repository') != 'false':
        raise ValueError('Full English history required for reproducible package timestamps; fetch with --unshallow or use fetch-depth: 0')
    value = git(english, 'log', '-1', '--format=%cI', 'HEAD', '--', *PACKAGE_INPUT_PATHS)
    if not value:
        raise ValueError('No committed English package inputs found')
    return datetime.fromisoformat(value).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def inventory(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): sha(p)
            for p in sorted((root / "src").rglob("*")) if p.is_file()}


def build(args) -> Path:
    if getattr(args, "tdk", None) is not None and not args.preview:
        raise ValueError("TDK override is a preview-only rehearsal")
    config = yaml.safe_load((ROOT / "pipeline.yml").read_text())
    if config.get("schema_version") != 2 or config.get("profile") != PO_PROFILE:
        raise ValueError("This build requires the committed official PO pipeline profile")
    target = dict(config["translation"])
    if args.translation_version is not None:
        if not args.preview:
            raise ValueError("Version override is a preview-only rehearsal")
        target["version"] = args.translation_version
    if (target.get("language") != "zh-Hant" or target.get("catalog") != "locales/zh-Hant.po"
            or target["organization_id"] != config["source"]["organization_id"]
            or target["template_id"] != config["source"]["template_id"] + "-zhtw-compat434"):
        raise ValueError("Chinese catalog and compatibility identity differ from this profile")
    english, tooling = args.english.resolve(), args.tooling.resolve()
    if not Path(dsw_document_template_tool.__file__).resolve().is_relative_to(tooling / "src"):
        raise ValueError("Imported tooling must come from the locked --tooling checkout")
    states = {
        "english": require_clean_lock(english, config["source"]["commit"], args.preview),
        "tooling": require_clean_lock(tooling, config["tooling"]["commit"], args.preview),
        "translation": fingerprint(ROOT),
    }
    if not args.preview and states["translation"]["dirty"]:
        raise ValueError("Release candidates require committed PO and configuration")
    if states["english"]["commit"] is None or states["tooling"]["commit"] is None:
        raise ValueError("Identified Git source and tooling checkouts are required")
    tdk = select_tdk(tooling, getattr(args, "tdk", None))
    actual_tdk = tdk_provenance(tdk)
    versions = {name: importlib.metadata.version(name)
                for name in ("dsw-tdk", "Jinja2", "polib", "python-docx")}
    expected = config["build_dependencies"]
    if versions != expected or actual_tdk["version"] != expected["dsw-tdk"]:
        raise ValueError("Build dependencies or TDK CLI differ from the exact pipeline lock")
    source_metadata = json.loads((english / "template.json").read_text())
    if (source_metadata.get("language") != "en"
            or source_metadata["metamodelVersion"] != config["runtime"]["metamodel"]):
        raise ValueError("English source language or template metamodel differs from pipeline")
    for key, config_key in (("organizationId", "organization_id"),
                            ("templateId", "template_id"), ("version", "version")):
        if source_metadata[key] != str(config["source"][config_key]):
            raise ValueError(f"Source metadata differs from pipeline lock: {key}")

    output_root = ROOT / "outputs"
    output_root.mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="build-", dir=output_root))
    timestamp = package_timestamp(english)
    prepared = output / "en"
    prepared.mkdir()
    shutil.copytree(english / "src", prepared / "src")
    for filename in ("template.json", "LICENSE"):
        shutil.copyfile(english / filename, prepared / filename)
    shutil.copyfile(package_readme(english), prepared / "README.md")
    set_template_language(source_metadata, "en")
    write_json(prepared / "template.json", source_metadata)
    font = tooling / "src/dsw_document_template_tool/resources/fonts/NotoSansTC-Variable.ttf"
    # Exactly one preparation: Chinese is a generated runtime profile of this
    # package, not a second reference/style preparation or translated Jinja fork.
    subprocess.run([sys.executable, str(english / "scripts/prepare_layout.py"),
                    "--template", str(prepared), "--font", str(font),
                    "--language", "en"], check=True)
    for license_file in font.parent.glob("*.txt"):
        shutil.copyfile(license_file, prepared / "src/fonts" / license_file.name)

    def tdk_run(label: str, *arguments: str) -> None:
        result = subprocess.run([str(tdk), "--no-config", "--no-dot-env", *map(str, arguments)],
                                capture_output=True, text=True)
        (output / (label + ".log")).write_text(result.stdout + result.stderr)
        if result.returncode:
            raise ValueError(f"TDK {label} failed; see {output / (label + '.log')}")

    tdk_run("english-verify", "verify", prepared)
    tdk_run("english-package", "package", prepared, "--output", output / "english.zip")
    canonicalize_zip(output / "english.zip", timestamp)
    shutil.copyfile(ROOT / target["catalog"], output / "zh-Hant.po")
    exporter_path = english / "scripts/export_legacy_locale.py"
    spec = importlib.util.spec_from_file_location("locked_legacy_exporter", exporter_path)
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    # Caller-supplied source provenance records the actual checkout. Preview
    # state is explicit in this manifest and remains ineligible for staging.
    exported = exporter.export_bundle(output / "english.zip", output / "zh-Hant.po",
                                      output / "chinese.zip", str(target["version"]),
                                      states["english"]["commit"])
    coordinate = ":".join(str(target[key]) for key in ("organization_id", "template_id", "version"))
    if exported["template_id"] != coordinate:
        raise ValueError("Generated Chinese coordinate differs from pipeline")
    with zipfile.ZipFile(output / "chinese.zip") as archive:
        (output / "zh-Hant.mo").write_bytes(archive.read(
            "template/assets/src/i18n/zh-Hant/LC_MESSAGES/dsw.mo"))
    if sha(output / "zh-Hant.mo") != exported["mo_sha256"]:
        raise ValueError("Generated catalog bytes differ from exporter provenance")
    tdk_run("chinese-unpackage", "unpackage", output / "chinese.zip",
            "--output", output / "translated")
    tdk_run("chinese-verify", "verify", output / "translated")
    english_inventory = inventory(prepared)
    chinese_inventory = inventory(output / "translated")
    mo_path = "src/i18n/zh-Hant/LC_MESSAGES/dsw.mo"
    language_path = "src/locales/language.j2"
    if set(chinese_inventory) != set(english_inventory) | {mo_path}:
        raise ValueError("Unexpected generated compatibility render inventory")
    if {name for name in english_inventory
            if english_inventory[name] != chinese_inventory[name]} != {language_path}:
        raise ValueError("Chinese generation changed shared render source or assets")
    final_states = {"english": fingerprint(english), "tooling": fingerprint(tooling),
                    "translation": fingerprint(ROOT)}
    if final_states != states:
        raise ValueError("Input checkout state changed during build; discard this candidate")
    write_json(output / "manifest.json", {
        "schema_version": 2, "profile": PO_PROFILE,
        "status": "preview" if args.preview else "candidate",
        "source": config["source"], "tooling": config["tooling"],
        "translation": target, "runtime": config["runtime"],
        "tdk": actual_tdk, "build_dependencies": versions,
        "package_timestamp": timestamp, "checkouts": states,
        "po": {"path": target["catalog"], "language": "zh-Hant",
               "sha256": sha(output / "zh-Hant.po"),
               "mo_sha256": sha(output / "zh-Hant.mo"),
               "messages": exported["approved_messages"]},
        "translation_units": exported["approved_messages"], "untranslated_units": [],
        "sha256": {name: sha(output / name) for name in PO_ARTIFACTS},
        "rendering": {"english": english_inventory, "compat434": chinese_inventory,
                      "reference_preparations": 1,
                      "exporter_sha256": sha(exporter_path),
                      "prepared_reference_sha256": sha(prepared / "src/word/reference.docx")},
        "publication_rule": "Build success is not acceptance. Require a report bound to all five artifact hashes and this manifest; never overwrite published versions.",
    })
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--english", type=Path, required=True)
    parser.add_argument("--tooling", type=Path, required=True)
    parser.add_argument("--tdk", type=Path, help="Preview-only CLI override")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--translation-version", help="Preview-only independent version rehearsal")
    print(build(parser.parse_args()))
