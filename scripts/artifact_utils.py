"""Canonical ZIP bytes and immutable, local candidate staging."""

import hashlib
import io
import json
import re
import shutil
import uuid
import zipfile
from pathlib import Path


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


def stage_candidate(build: Path, store: Path) -> Path:
    manifest = json.loads((build / "manifest.json").read_text())
    report = json.loads((build / "pilot-report.json").read_text())
    if manifest["status"] != "candidate" or manifest["untranslated_units"]:
        raise ValueError("Only locked, fully translated candidate builds may be staged")
    if report.get("passed") is not True or report.get("blocking_issues"):
        raise ValueError("Candidate has not passed the declared acceptance scope")
    for name in ("english.zip", "chinese.zip"):
        if sha(build / name) != manifest["sha256"][name]:
            raise ValueError(f"Artifact differs from manifest: {name}")
    # Bind the test report to the exact packages, not another build's report.
    if report.get("package_sha256") != {
        name: manifest["sha256"][name] for name in ("english.zip", "chinese.zip")
    }:
        raise ValueError("Acceptance report is not bound to these packages")
    target = manifest["translation"]
    fields = [str(target[key]) for key in ("organization_id", "template_id", "version")]
    if not all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+-]*", value) for value in fields):
        raise ValueError("Unsafe candidate identity")
    destination = store / "--".join(fields)
    store.mkdir(parents=True, exist_ok=True)
    # Atomic reservation. Even identical bytes cannot replace a staged version.
    destination.mkdir()
    for name in ("english.zip", "chinese.zip", "manifest.json", "pilot-report.json"):
        shutil.copyfile(build / name, destination / name)
    return destination
