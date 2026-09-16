import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from compare_worker_replays import page_geometry, validate_reports
from prepare_runtime_variant import TABLES_ONLY_SOURCES, require_tables_only_sources

spec = importlib.util.spec_from_file_location('patch_fonts', ROOT/'experiments/worker-pdf-stability/patch_fonts.py')
patch_fonts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch_fonts)


class WorkerStabilityTests(unittest.TestCase):
    def test_font_experiment_cannot_be_mislabeled_as_tables_only(self):
        require_tables_only_sources(dict(TABLES_ONLY_SOURCES))
        for name in TABLES_ONLY_SOURCES:
            with self.assertRaises(ValueError):
                require_tables_only_sources(dict(TABLES_ONLY_SOURCES, **{name: 'different'}))
        with self.assertRaises(ValueError):
            require_tables_only_sources({'dsw.document_worker.model.utils': TABLES_ONLY_SOURCES['dsw.document_worker.model.utils']})

    def sources(self):
        # Compilable synthetic modules containing the exact mechanical anchors.
        return {name: b'"""\n'+b'\n'.join(old for old, new in pairs)+b'\n"""\n'
            for name, pairs in patch_fonts.REPLACEMENTS.items()}

    def test_unknown_sources_rejected(self):
        with self.assertRaises(ValueError):
            patch_fonts.patched_sources({'fonts': b'unknown', 'ffi': b'unknown'})

    def test_missing_or_extra_file_rejected(self):
        for sources in ({}, {'fonts': b'one'}, dict(self.sources(), other=b'x')):
            with self.assertRaises(ValueError): patch_fonts.patched_sources(sources)

    def test_exact_replacements_and_reapplication_rejected(self):
        sources = self.sources()
        expected = {name: hashlib.sha256(data).hexdigest() for name, data in sources.items()}
        with patch.dict(patch_fonts.EXPECTED, expected, clear=True):
            result = patch_fonts.patched_sources(sources)
            for name, pairs in patch_fonts.REPLACEMENTS.items():
                wanted = sources[name]
                for old, new in pairs: wanted = wanted.replace(old, new)
                self.assertEqual(result[name], wanted)
            with self.assertRaises(ValueError): patch_fonts.patched_sources(result)

    def test_missing_or_duplicate_anchor_rejected_even_with_matching_hash(self):
        for duplicated in (False, True):
            sources = self.sources()
            old = patch_fonts.REPLACEMENTS['fonts'][0][0]
            sources['fonts'] = sources['fonts'].replace(old, old+b'\n'+old if duplicated else b'changed')
            expected = {name: hashlib.sha256(data).hexdigest() for name, data in sources.items()}
            with patch.dict(patch_fonts.EXPECTED, expected, clear=True), self.assertRaises(ValueError):
                patch_fonts.patched_sources(sources)

    def test_geometry_retains_punctuation_and_coordinates_but_not_metadata(self):
        data = b'<doc><title>Ignore creation time</title><page width="600" height="800"><word xMin="12" yMin="30">Answer.</word></page></doc>'
        self.assertEqual(page_geometry(data), [[{'width': '600', 'height': '800'}, [{'xMin': '12', 'yMin': '30', 'text': 'Answer.'}]]])
        for old, new in ((b'Answer.', b'Answer'), (b'xMin="12"', b'xMin="13"')):
            self.assertNotEqual(page_geometry(data), page_geometry(data.replace(old, new)))

    def test_replay_inputs_and_runner_must_match(self):
        baseline = {'completed_without_crash': True, 'probe': 'render', 'sequence': ['a.html'],
            'source_sha256': {'a.html': 'exact'}, 'runner_sha256': 'runner', 'gc_policy': 'natural'}
        validate_reports(baseline, dict(baseline))
        for key, value in [('completed_without_crash', False), ('probe', 'font-lifetime'), ('sequence', ['b.html']),
            ('source_sha256', {'a.html': 'other'}), ('runner_sha256', 'other'), ('gc_policy', 'after-each')]:
            with self.assertRaises(ValueError): validate_reports(baseline, dict(baseline, **{key: value}))


if __name__ == '__main__':
    unittest.main()
