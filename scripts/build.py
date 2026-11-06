"""Build a shared English DT, authoritative Chinese PO, and generated 4.34 DT."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import yaml

from artifact_utils import PO_ARTIFACTS, PO_PROFILE

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


def inventory(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): sha(p)
            for p in sorted((root / "src").rglob("*")) if p.is_file()}


def load_english_package_builder(english: Path):
    """Load the package API from the source checkout whose commit the caller locked."""
    path = english / "scripts/build_package.py"
    spec = importlib.util.spec_from_file_location("locked_english_package_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(args) -> Path:
    if getattr(args, "tdk", None) is not None and not args.preview:
        raise ValueError("TDK override is a preview-only rehearsal")
    config = yaml.safe_load((ROOT / "pipeline.yml").read_text())
    if config.get("schema_version") != 3 or config.get("profile") != PO_PROFILE or "tooling" in config:
        raise ValueError("This build requires the schema 3 source-owned English package pipeline")
    target = dict(config["translation"])
    if args.translation_version is not None:
        if not args.preview:
            raise ValueError("Version override is a preview-only rehearsal")
        target["version"] = args.translation_version
    if (target.get("language") != "zh-Hant" or target.get("catalog") != "locales/zh-Hant.po"
            or target["organization_id"] != config["source"]["organization_id"]
            or target["template_id"] != config["source"]["template_id"] + "-zhtw-compat434"):
        raise ValueError("Chinese catalog and compatibility identity differ from this profile")
    english = args.english.resolve()
    states = {
        "english": require_clean_lock(english, config["source"]["commit"], args.preview),
        "translation": fingerprint(ROOT),
    }
    if not args.preview and states["translation"]["dirty"]:
        raise ValueError("Release candidates require committed PO and configuration")
    if any(state["commit"] is None for state in states.values()):
        raise ValueError("Identified Git source and translation checkouts are required")
    package_builder = load_english_package_builder(english)
    tdk = package_builder.select_tdk(getattr(args, "tdk", None))
    actual_tdk = package_builder.tdk_provenance(tdk)
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
    prepared = output / "en"
    # The English source owns its preparation, font assets and deterministic ZIP.
    # Chinese generation consumes that package; it never prepares layout again.
    packaged = package_builder.build_package(english, output, tdk)
    timestamp = packaged["package_timestamp"]
    if packaged["tdk"] != actual_tdk:
        raise ValueError("TDK CLI changed during English package generation")

    def tdk_run(label: str, *arguments: str) -> None:
        result = subprocess.run([str(tdk), "--no-config", "--no-dot-env", *map(str, arguments)],
                                capture_output=True, text=True)
        (output / (label + ".log")).write_text(result.stdout + result.stderr)
        if result.returncode:
            raise ValueError(f"TDK {label} failed; see {output / (label + '.log')}")

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
    final_states = {"english": fingerprint(english), "translation": fingerprint(ROOT)}
    if final_states != states:
        raise ValueError("Input checkout state changed during build; discard this candidate")
    write_json(output / "manifest.json", {
        "schema_version": 3, "profile": PO_PROFILE,
        "status": "preview" if args.preview else "candidate",
        "source": config["source"],
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
    parser.add_argument("--tdk", type=Path, help="Preview-only CLI override")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--translation-version", help="Preview-only independent version rehearsal")
    print(build(parser.parse_args()))
