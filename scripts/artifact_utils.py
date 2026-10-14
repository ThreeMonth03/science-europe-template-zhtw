"""Canonical ZIP bytes and immutable, local candidate staging."""

import hashlib
import io
import json
import re
import shutil
import uuid
import zipfile
from pathlib import Path

PO_PROFILE = "official-po-with-compat434"
PO_ARTIFACTS = ("english.zip", "chinese.zip", "zh-Hant.po", "zh-Hant.mo", "chinese.zip.json")
MO_MEMBER = "template/assets/src/i18n/zh-Hant/LC_MESSAGES/dsw.mo"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonicalize_zip(path: Path, timestamp: str) -> None:
    result = io.BytesIO()
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(result, "w") as target:
        for name in sorted(source.namelist()):
            content = source.read(name)
            if name == "template/template.json":
                payload = json.loads(content)
                payload["createdAt"] = payload["updatedAt"] = timestamp
                for kind in ("files", "assets"):
                    for item in payload[kind]:
                        item["uuid"] = str(
                            uuid.uuid5(
                                uuid.NAMESPACE_URL,
                                f"dsw-template/{payload['id']}/{kind}/{item['fileName']}",
                            )
                        )
                    payload[kind].sort(key=lambda item: item["fileName"])
                content = (
                    json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
                ).encode()
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            target.writestr(info, content)
    path.write_bytes(result.getvalue())


def validate_po_candidate(build: Path, manifest: dict, report: dict) -> None:
    """Bind both runtime deliveries to the same reviewed source and catalog."""
    import polib

    hashes = manifest.get("sha256", {})
    if set(hashes) != set(PO_ARTIFACTS):
        raise ValueError("PO candidates require exactly five distributable artifact hashes")
    for name in PO_ARTIFACTS:
        if not (build / name).is_file() or sha(build / name) != hashes[name]:
            raise ValueError(f"Artifact differs from manifest or is missing: {name}")
    if report.get("package_sha256") != hashes:
        raise ValueError("Acceptance report is not bound to all PO candidate artifacts")
    if report.get("manifest_sha256") != sha(build / "manifest.json"):
        raise ValueError("Acceptance report is not bound to this manifest")

    checkouts = manifest.get("checkouts", {})
    for name in ("source", "tooling"):
        commit = manifest.get(name, {}).get("commit", "")
        state = checkouts.get("english" if name == "source" else name, {})
        if (
            not re.fullmatch(r"[0-9a-f]{40}", commit)
            or state.get("commit") != commit
            or state.get("dirty") is not False
        ):
            raise ValueError(f"PO candidate requires a clean, locked {name} checkout")
    translation_state = checkouts.get("translation", {})
    if (
        not re.fullmatch(r"[0-9a-f]{40}", translation_state.get("commit", ""))
        or translation_state.get("dirty") is not False
    ):
        raise ValueError("PO candidate requires a clean, identified translation checkout")

    po_metadata = manifest.get("po", {})
    if (
        po_metadata.get("path") != "locales/zh-Hant.po"
        or po_metadata.get("language") != "zh-Hant"
        or po_metadata.get("sha256") != hashes["zh-Hant.po"]
        or po_metadata.get("mo_sha256") != hashes["zh-Hant.mo"]
        or type(po_metadata.get("messages")) is not int
        or po_metadata["messages"] <= 0
    ):
        raise ValueError("PO provenance differs from candidate artifacts")
    po = polib.pofile(str(build / "zh-Hant.po"))
    entries = [entry for entry in po if not entry.obsolete]
    if (
        po.metadata.get("Language") != "zh-Hant"
        or len(entries) != po_metadata["messages"]
        or len({(entry.msgctxt, entry.msgid) for entry in entries}) != len(entries)
        or any(not entry.msgstr.strip() or "fuzzy" in entry.flags or entry.msgid_plural for entry in entries)
        or po.to_binary() != (build / "zh-Hant.mo").read_bytes()
    ):
        raise ValueError("PO and MO must be the same complete zh-Hant catalog")

    target = manifest["translation"]
    coordinate = ":".join(str(target[key]) for key in ("organization_id", "template_id", "version"))
    expected = {
        "profile": "legacy434-zh-Hant-v1",
        "source_commit": manifest["source"]["commit"],
        "source_zip_sha256": hashes["english.zip"],
        "po_sha256": hashes["zh-Hant.po"],
        "mo_sha256": hashes["zh-Hant.mo"],
        "output_zip_sha256": hashes["chinese.zip"],
        "approved_messages": po_metadata["messages"],
        "template_id": coordinate,
    }
    sidecar = json.loads((build / "chinese.zip.json").read_text())
    if any(sidecar.get(key) != value for key, value in expected.items()):
        raise ValueError("Compatibility exporter provenance does not match this source/PO pair")
    with zipfile.ZipFile(build / "chinese.zip") as archive:
        metadata = json.loads(archive.read("template/template.json"))
        if metadata.get("id") != coordinate or metadata.get("language") != "zh-Hant":
            raise ValueError("Compatibility package identity differs from manifest")
        if archive.read(MO_MEMBER) != (build / "zh-Hant.mo").read_bytes():
            raise ValueError("Compatibility package embeds a different MO catalog")
    source = manifest["source"]
    source_coordinate = ":".join(str(source[key]) for key in ("organization_id", "template_id", "version"))
    with zipfile.ZipFile(build / "english.zip") as archive:
        metadata = json.loads(archive.read("template/template.json"))
        if metadata.get("id") != source_coordinate or metadata.get("language") != "en":
            raise ValueError("English package identity differs from source lock")


def stage_candidate(build: Path, store: Path) -> Path:
    manifest = json.loads((build / "manifest.json").read_text())
    report = json.loads((build / "pilot-report.json").read_text())
    if manifest["status"] != "candidate" or manifest["untranslated_units"]:
        raise ValueError("Only locked, fully translated candidate builds may be staged")
    if report.get("passed") is not True or report.get("blocking_issues"):
        raise ValueError("Candidate has not passed the declared acceptance scope")
    if "profile" in manifest:
        if manifest["profile"] != PO_PROFILE:
            raise ValueError("Unknown explicit candidate profile")
        validate_po_candidate(build, manifest, report)
        artifacts = PO_ARTIFACTS
    else:
        if "po" in manifest or any(name in manifest.get("sha256", {}) for name in PO_ARTIFACTS[2:]):
            raise ValueError("PO candidate artifacts require an explicit PO profile")
        artifacts = ("english.zip", "chinese.zip")
        for name in artifacts:
            if sha(build / name) != manifest["sha256"][name]:
                raise ValueError(f"Artifact differs from manifest: {name}")
        # Historical two-package candidates retain their original contract.
        if report.get("package_sha256") != {name: manifest["sha256"][name] for name in artifacts}:
            raise ValueError("Acceptance report is not bound to these packages")
    target = manifest["translation"]
    fields = [str(target[key]) for key in ("organization_id", "template_id", "version")]
    if not all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+-]*", value) for value in fields):
        raise ValueError("Unsafe candidate identity")
    destination = store / "--".join(fields)
    store.mkdir(parents=True, exist_ok=True)
    # Atomic reservation. Even identical bytes cannot replace a staged version.
    destination.mkdir()
    for name in (*artifacts, "manifest.json", "pilot-report.json"):
        shutil.copyfile(build / name, destination / name)
    return destination
