"""Builder wiring with real PO export, mocked TDK, and opaque (non-Word) assets."""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import polib
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build as builder  # noqa: E402
from artifact_utils import PO_ARTIFACTS, sha  # noqa: E402


class POBuildTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        self.zh, self.en, self.tool = [base / name for name in ("zh", "english", "tooling")]
        for path in (self.zh / "locales", self.zh / "translation", self.en / "src/locales", self.en / "src/word", self.en / "scripts", self.tool / "src"):
            path.mkdir(parents=True)
        self.history = self.zh / "translation/sentinel.md"
        self.history.write_text("Historical tree: never refresh from the PO build.")
        config = yaml.safe_load((ROOT / "pipeline.yml").read_text())
        self.config = config
        config["source"].update(commit="a" * 40, organization_id="example", template_id="template")
        config["tooling"]["commit"] = "b" * 40
        config["translation"].update(organization_id="example", template_id="template-zhtw-compat434")
        self.config_path = self.zh / "pipeline.yml"
        self.config_path.write_text(yaml.safe_dump(config))
        self.metadata = {"organizationId": "example", "templateId": "template", "version": config["source"]["version"],
                         "metamodelVersion": "18.0", "language": "en", "formats": []}
        (self.en / "template.json").write_text(json.dumps(self.metadata))
        (self.en / "LICENSE").write_text("Test fixture license")
        (self.en / "PACKAGE_README.md").write_text("Test fixture only")
        (self.en / "src/locales/language.j2").write_text("en")
        (self.en / "src/main.j2").write_text("{{ pgettext('test', 'Dataset') }}")
        (self.en / "src/word/reference.docx").write_bytes(b"opaque unit-test asset, not a DOCX")
        po = polib.POFile()
        po.metadata = {"Language": "zh-Hant", "Content-Type": "text/plain; charset=UTF-8"}
        po.append(polib.POEntry(msgctxt="test", msgid="Dataset", msgstr="資料集"))
        po.save(str(self.zh / "locales/zh-Hant.po"))
        self.states = {self.en: {"commit": "a" * 40, "dirty": False}, self.tool: {"commit": "b" * 40, "dirty": False}, self.zh: {"commit": "c" * 40, "dirty": False}}
        self.args = SimpleNamespace(english=self.en, tooling=self.tool, preview=False, tdk=None, refresh=False, seed_tree=None, translation_version=None)
        self.calls = []
        stack = ExitStack()
        self.addCleanup(stack.close)
        for mock in (
            patch.object(builder, "ROOT", self.zh),
            patch.object(builder.dsw_document_template_tool, "__file__", str(self.tool / "src/tool.py")),
            patch.object(builder, "fingerprint", side_effect=lambda path: dict(self.states[path])),
            patch.object(builder, "tdk_provenance", return_value={"version": config["build_dependencies"]["dsw-tdk"]}),
            patch.object(builder.importlib.metadata, "version", side_effect=config["build_dependencies"].__getitem__),
            patch.object(builder, "package_timestamp", return_value="2026-10-14T00:00:00Z"),
            patch.object(builder.subprocess, "run", side_effect=self.tdk_run),
        ):
            stack.enter_context(mock)

    def tdk_run(self, command, **kwargs):
        self.calls.append(command)
        if command[1].endswith("prepare_layout.py"):
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        operation = command[3]
        if operation == "package":
            prepared, output = Path(command[4]), Path(command[-1])
            payload = json.loads((prepared / "template.json").read_text())
            payload.update(id=f"example:template:{payload['version']}", files=[], assets=[])
            with zipfile.ZipFile(output, "w") as archive:
                for path in sorted((prepared / "src").rglob("*")):
                    if not path.is_file():
                        continue
                    name = path.relative_to(prepared).as_posix()
                    entry = {"fileName": name}
                    if path.suffix == ".j2":
                        entry["content"] = path.read_text()
                        payload["files"].append(entry)
                    else:
                        payload["assets"].append(entry)
                        archive.writestr("template/assets/" + name, path.read_bytes())
                archive.writestr("template/template.json", json.dumps(payload))
        elif operation == "unpackage":
            destination = Path(command[-1])
            with zipfile.ZipFile(command[4]) as archive:
                payload = json.loads(archive.read("template/template.json"))
                for entry in payload["files"] + payload["assets"]:
                    path = destination / entry["fileName"]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(entry["content"].encode() if "content" in entry else archive.read("template/assets/" + entry["fileName"]))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def run_full_build(self):
        source = Path(os.environ.get("DSW_ENGLISH_CHECKOUT", ROOT.parent / "english")) / "scripts/export_legacy_locale.py"
        if not source.is_file():
            raise RuntimeError("Set DSW_ENGLISH_CHECKOUT to the locked English checkout containing scripts/export_legacy_locale.py")
        shutil.copyfile(source, self.en / "scripts/export_legacy_locale.py")
        spec = importlib.util.spec_from_file_location("fixture_exporter", source)
        exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exporter)
        self.metadata["formats"] = [{"uuid": identifier, "name": "Fixture", "steps": [{"name": "jinja", "options": {}}]} for identifier in exporter.FORMAT_NAMES]
        (self.en / "template.json").write_text(json.dumps(self.metadata))
        before = self.history.read_bytes()
        result = builder.build(self.args)
        self.assertEqual(before, self.history.read_bytes())
        self.assertEqual([self.history], list((self.zh / "translation").iterdir()))
        prepares = [call for call in self.calls if call[1].endswith("prepare_layout.py")]
        self.assertEqual(1, len(prepares))
        self.assertEqual("en", prepares[0][-1])
        manifest = json.loads((result / "manifest.json").read_text())
        self.assertEqual({name: sha(result / name) for name in PO_ARTIFACTS}, manifest["sha256"])
        self.assertEqual(polib.pofile(str(result / "zh-Hant.po")).to_binary(), (result / "zh-Hant.mo").read_bytes())
        sidecar = json.loads((result / "chinese.zip.json").read_text())
        for field, filename in (("source_zip_sha256", "english.zip"), ("po_sha256", "zh-Hant.po"), ("mo_sha256", "zh-Hant.mo"), ("output_zip_sha256", "chinese.zip")):
            self.assertEqual(sha(result / filename), sidecar[field])
        return manifest

    def test_candidate_has_one_preparation_and_one_source_po_pair(self):
        self.assertEqual("candidate", self.run_full_build()["status"])

    def test_preview_records_dirty_checkouts_without_mutating_history(self):
        self.args.preview = True
        for state in self.states.values():
            state["dirty"] = True
        manifest = self.run_full_build()
        self.assertEqual("preview", manifest["status"])
        self.assertTrue(all(state["dirty"] for state in manifest["checkouts"].values()))

    def test_candidate_rejects_dirty_or_mismatched_source_and_tool_locks(self):
        for checkout in (self.en, self.tool, self.zh):
            for state in ({"commit": self.states[checkout]["commit"], "dirty": True}, {"commit": "d" * 40, "dirty": False}):
                if checkout == self.zh and not state["dirty"]:
                    continue  # The translation HEAD is recorded, not a self-referential lock.
                original, self.states[checkout] = self.states[checkout], state
                with self.subTest(checkout=checkout, state=state), self.assertRaises(ValueError):
                    builder.build(self.args)
                self.states[checkout] = original
        self.assertFalse((self.zh / "outputs").exists())

    def test_dependency_mismatch_fails_before_preparation(self):
        with patch.object(builder.importlib.metadata, "version", return_value="wrong"), self.assertRaises(ValueError):
            builder.build(self.args)
        self.assertEqual([], self.calls)

    def test_source_language_and_template_metamodel_must_match(self):
        for key, value in (("language", "zh-Hant"), ("metamodelVersion", "18.3")):
            original = self.metadata[key]
            self.metadata[key] = value
            (self.en / "template.json").write_text(json.dumps(self.metadata))
            with self.subTest(key=key), self.assertRaises(ValueError):
                builder.build(self.args)
            self.metadata[key] = original
        self.assertEqual([], self.calls)

    def test_checkout_change_during_build_prevents_a_manifest(self):
        run = self.tdk_run
        def changed(command, **kwargs):
            result = run(command, **kwargs)
            self.states[self.zh]["dirty"] = True
            return result
        with patch.object(builder.subprocess, "run", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "state changed during build"):
                self.run_full_build()
        self.assertFalse(list((self.zh / "outputs").glob("*/manifest.json")))

    def test_old_refresh_options_and_candidate_overrides_fail_closed(self):
        for key, value in (("refresh", True), ("seed_tree", self.zh / "translation"), ("tdk", self.tool / "custom-tdk"), ("translation_version", "0.3.999")):
            setattr(self.args, key, value)
            with self.subTest(option=key), self.assertRaises(ValueError):
                builder.build(self.args)
            setattr(self.args, key, False if key == "refresh" else None)
        self.assertEqual([], self.calls)


if __name__ == "__main__":
    unittest.main()
