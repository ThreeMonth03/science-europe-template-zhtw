import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from artifact_utils import canonicalize_zip, sha, stage_candidate  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
