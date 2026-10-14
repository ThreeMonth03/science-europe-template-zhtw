import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from artifact_utils import MO_MEMBER, PO_ARTIFACTS, PO_PROFILE, canonicalize_zip, sha, stage_candidate  # noqa: E402
from build import require_clean_lock  # noqa: E402


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.build = self.root / "build"
        self.build.mkdir()
        for name in ("english.zip", "chinese.zip"):
            (self.build / name).write_bytes(name.encode())
        hashes = {name: sha(self.build / name) for name in ("english.zip", "chinese.zip")}
        self.manifest = {
            "status": "candidate",
            "untranslated_units": [],
            "sha256": hashes,
            "translation": {"organization_id": "example", "template_id": "zh", "version": "0.1.0"},
        }
        self.report = {"passed": True, "package_sha256": hashes}
        self.save()

    def save(self):
        (self.build / "manifest.json").write_text(json.dumps(self.manifest))
        (self.build / "pilot-report.json").write_text(json.dumps(self.report))

    def test_version_can_never_be_overwritten(self):
        destination = stage_candidate(self.build, self.root / "store")
        before = sha(destination / "chinese.zip")
        with self.assertRaises(FileExistsError):
            stage_candidate(self.build, self.root / "store")
        self.assertEqual(before, sha(destination / "chinese.zip"))

    def test_preview_is_rejected(self):
        self.manifest["status"] = "preview"
        self.save()
        with self.assertRaises(ValueError):
            stage_candidate(self.build, self.root / "store")
        self.assertFalse((self.root / "store").exists())

    def test_runtime_experiment_is_not_a_template_candidate(self):
        self.manifest['status'] = 'runtime-experiment'
        self.save()
        with self.assertRaises(ValueError):
            stage_candidate(self.build, self.root / 'store')
        self.assertFalse((self.root / 'store').exists())

    def test_untranslated_candidate_is_rejected(self):
        self.manifest["untranslated_units"] = ["missing"]
        self.save()
        with self.assertRaises(ValueError):
            stage_candidate(self.build, self.root / "store")

    def test_known_acceptance_failure_blocks_staging(self):
        self.report.update(passed=False, blocking_issues=["markdown-table-unsupported"])
        self.save()
        with self.assertRaises(ValueError):
            stage_candidate(self.build, self.root / "store")

    def test_changed_package_is_rejected(self):
        (self.build / "chinese.zip").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            stage_candidate(self.build, self.root / "store")

    def test_report_from_another_build_is_rejected(self):
        self.report["package_sha256"] = {}
        self.save()
        with self.assertRaises(ValueError):
            stage_candidate(self.build, self.root / "store")

    def test_identity_cannot_escape_store(self):
        self.manifest["translation"]["version"] = "../../outside"
        self.save()
        with self.assertRaises(ValueError):
            stage_candidate(self.build, self.root / "store")

    def test_source_and_tool_checkouts_must_be_clean_and_locked(self):
        for state in ({"commit": "correct", "dirty": True}, {"commit": "wrong", "dirty": False}):
            with patch("build.fingerprint", return_value=state), self.assertRaises(ValueError):
                require_clean_lock(self.root, "correct", False)
        with patch("build.fingerprint", return_value={"commit": "correct", "dirty": False}):
            self.assertEqual("correct", require_clean_lock(self.root, "correct", False)["commit"])

    def test_tdk_build_metadata_is_canonicalized(self):
        for number in (1, 2):
            payload = {
                "id": "example:template:0.1.0",
                "createdAt": str(number),
                "updatedAt": str(number),
                "files": [{"uuid": str(number), "fileName": "src/test.j2", "content": "Hello"}],
                "assets": [],
            }
            file = self.root / f"{number}.zip"
            with zipfile.ZipFile(file, "w") as archive:
                archive.writestr("template/template.json", json.dumps(payload))
            canonicalize_zip(file, "2026-09-11T00:00:00Z")
        self.assertEqual(sha(self.root / "1.zip"), sha(self.root / "2.zip"))


class POCandidateTests(unittest.TestCase):
    def setUp(self):
        import polib

        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.build = self.root / "build"
        self.build.mkdir()
        po = polib.POFile()
        po.metadata = {"Language": "zh-Hant", "Content-Type": "text/plain; charset=UTF-8"}
        po.append(polib.POEntry(msgctxt="test", msgid="Dataset", msgstr="資料集"))
        po.save(str(self.build / "zh-Hant.po"))
        po.save_as_mofile(str(self.build / "zh-Hant.mo"))
        for filename, identity, language in (
            ("english.zip", "example:template:0.3.78", "en"),
            ("chinese.zip", "example:template-zhtw-compat434:0.3.81", "zh-Hant"),
        ):
            with zipfile.ZipFile(self.build / filename, "w") as archive:
                archive.writestr("template/template.json", json.dumps({"id": identity, "language": language}))
                if filename == "chinese.zip":
                    archive.writestr(MO_MEMBER, (self.build / "zh-Hant.mo").read_bytes())
        self.sidecar = {
            "profile": "legacy434-zh-Hant-v1",
            "source_commit": "a" * 40,
            "source_zip_sha256": sha(self.build / "english.zip"),
            "po_sha256": sha(self.build / "zh-Hant.po"),
            "mo_sha256": sha(self.build / "zh-Hant.mo"),
            "output_zip_sha256": sha(self.build / "chinese.zip"),
            "approved_messages": 1,
            "template_id": "example:template-zhtw-compat434:0.3.81",
        }
        (self.build / "chinese.zip.json").write_text(json.dumps(self.sidecar))
        self.manifest = {
            "profile": PO_PROFILE,
            "status": "candidate",
            "untranslated_units": [],
            "source": {"commit": "a" * 40, "organization_id": "example", "template_id": "template", "version": "0.3.78"},
            "tooling": {"commit": "b" * 40},
            "translation": {"organization_id": "example", "template_id": "template-zhtw-compat434", "version": "0.3.81"},
            "checkouts": {
                "english": {"commit": "a" * 40, "dirty": False},
                "tooling": {"commit": "b" * 40, "dirty": False},
                "translation": {"commit": "c" * 40, "dirty": False},
            },
            "po": {
                "path": "locales/zh-Hant.po", "language": "zh-Hant",
                "sha256": sha(self.build / "zh-Hant.po"),
                "mo_sha256": sha(self.build / "zh-Hant.mo"), "messages": 1,
            },
            "sha256": {name: sha(self.build / name) for name in PO_ARTIFACTS},
        }
        self.report = {"passed": True, "package_sha256": dict(self.manifest["sha256"])}
        self.save()

    def save(self, bind_manifest=True):
        (self.build / "manifest.json").write_text(json.dumps(self.manifest))
        if bind_manifest:
            self.report["manifest_sha256"] = sha(self.build / "manifest.json")
        (self.build / "pilot-report.json").write_text(json.dumps(self.report))

    def assert_rejected(self):
        with self.assertRaises(ValueError):
            stage_candidate(self.build, self.root / "store")
        self.assertFalse((self.root / "store").exists())

    def test_all_po_deliveries_and_provenance_are_staged(self):
        destination = stage_candidate(self.build, self.root / "store")
        self.assertEqual(set(PO_ARTIFACTS) | {"manifest.json", "pilot-report.json"}, {path.name for path in destination.iterdir()})
        for name in PO_ARTIFACTS:
            self.assertEqual(sha(self.build / name), sha(destination / name))
        with self.assertRaises(FileExistsError):
            stage_candidate(self.build, self.root / "store")

    def test_changed_po_or_mo_is_rejected(self):
        for name in ("zh-Hant.po", "zh-Hant.mo"):
            with self.subTest(name=name):
                path = self.build / name
                original = path.read_bytes()
                path.write_bytes(original + b"changed")
                self.assert_rejected()
                path.write_bytes(original)

    def test_every_required_artifact_must_exist(self):
        for name in PO_ARTIFACTS:
            with self.subTest(name=name):
                path = self.build / name
                original = path.read_bytes()
                path.unlink()
                self.assert_rejected()
                path.write_bytes(original)

    def test_manifest_transplant_cannot_reuse_report_for_identical_packages(self):
        self.manifest["checkouts"]["translation"]["commit"] = "d" * 40
        self.save(bind_manifest=False)
        self.assert_rejected()

    def test_report_transplant_cannot_drop_po_artifact_bindings(self):
        self.report["package_sha256"] = {name: self.manifest["sha256"][name] for name in ("english.zip", "chinese.zip")}
        self.save()
        self.assert_rejected()

    def test_missing_manifest_binding_is_rejected(self):
        self.report.pop("manifest_sha256")
        self.save(bind_manifest=False)
        self.assert_rejected()

    def test_undeclared_extra_artifact_hash_is_rejected(self):
        self.manifest["sha256"]["other.zip"] = "f" * 64
        self.report["package_sha256"] = dict(self.manifest["sha256"])
        self.save()
        self.assert_rejected()

    def test_crosspaired_exporter_sidecar_is_rejected_even_when_rehashed(self):
        self.sidecar["source_zip_sha256"] = "f" * 64
        (self.build / "chinese.zip.json").write_text(json.dumps(self.sidecar))
        self.manifest["sha256"]["chinese.zip.json"] = sha(self.build / "chinese.zip.json")
        self.report["package_sha256"] = dict(self.manifest["sha256"])
        self.save()
        self.assert_rejected()

    def test_rehashed_mo_must_still_compile_from_the_po(self):
        (self.build / "zh-Hant.mo").write_bytes(b"unrelated MO")
        self.manifest["sha256"]["zh-Hant.mo"] = sha(self.build / "zh-Hant.mo")
        self.manifest["po"]["mo_sha256"] = self.manifest["sha256"]["zh-Hant.mo"]
        self.report["package_sha256"] = dict(self.manifest["sha256"])
        self.save()
        self.assert_rejected()

    def test_rehashed_compatibility_zip_cannot_embed_a_different_mo(self):
        path = self.build / "chinese.zip"
        with zipfile.ZipFile(path) as archive:
            descriptor = archive.read("template/template.json")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("template/template.json", descriptor)
            archive.writestr(MO_MEMBER, b"unrelated embedded MO")
        self.manifest["sha256"]["chinese.zip"] = sha(path)
        self.sidecar["output_zip_sha256"] = sha(path)
        (self.build / "chinese.zip.json").write_text(json.dumps(self.sidecar))
        self.manifest["sha256"]["chinese.zip.json"] = sha(self.build / "chinese.zip.json")
        self.report["package_sha256"] = dict(self.manifest["sha256"])
        self.save()
        self.assert_rejected()

    def test_missing_profile_cannot_downgrade_po_candidate_to_legacy(self):
        self.manifest.pop("profile")
        self.report["package_sha256"] = {name: self.manifest["sha256"][name] for name in ("english.zip", "chinese.zip")}
        self.save()
        self.assert_rejected()

    def test_unknown_explicit_profiles_are_rejected(self):
        for profile in (None, "", "legacy", "future-po"):
            with self.subTest(profile=profile):
                self.manifest["profile"] = profile
                self.save()
                self.assert_rejected()

    def test_missing_po_provenance_cannot_fall_back_to_two_packages(self):
        self.manifest.pop("po")
        self.save()
        self.assert_rejected()

    def test_checkouts_must_be_complete_clean_commits(self):
        for name in ("english", "tooling", "translation"):
            for replacement in ({"commit": "short", "dirty": False}, {"commit": "a" * 40, "dirty": True}):
                with self.subTest(name=name, replacement=replacement):
                    original = self.manifest["checkouts"][name]
                    self.manifest["checkouts"][name] = replacement
                    self.save()
                    self.assert_rejected()
                    self.manifest["checkouts"][name] = original

    def test_po_candidate_identity_cannot_escape_store(self):
        self.manifest["translation"]["version"] = "../../outside"
        self.save()
        self.assert_rejected()


if __name__ == "__main__":
    unittest.main()
