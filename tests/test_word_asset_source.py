from collections import Counter
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-word-asset'
sys.path[:0] = [str(ROOT / 'experiments/word-asset'), str(ROOT / 'scripts')]
from asset_recipe import HERE, XML, LUA, baseline, helper, patch, sha
from source_rehearsal import adapt_prose, FILES
from source_parity import run as compare_sources
from probe_pdf_budget_translation import pair


def english_root():
    return next(p for p in [ROOT.parent / 'english', ROOT.parent / 'science-europe-template']
                if (p / 'scripts/output_profile_contract.py').is_file())


class WordAssetSourceTests(unittest.TestCase):
    def test_english_adaptations_are_exact_reversible_and_stay_in_two_files(self):
        frozen = ARCHIVE / 'source-rehearsal'; proof = json.loads((frozen / 'source-proof.json').read_text())
        source = {f['fileName']: f['content'] for f in baseline('english')['files']}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in proof['source_adaptations']:
                p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(source[name])
            self.assertEqual(adapt_prose(root), proof['source_adaptations'])
            for name in proof['source_adaptations']:
                self.assertEqual((root / name).read_bytes(), (frozen / 'source' / name).read_bytes())
            with self.assertRaises(AssertionError): adapt_prose(root)
        self.assertEqual(len(proof['source_adaptations']), 2)
        old, new = proof['before_source_sha256'], proof['after_source_sha256']
        self.assertEqual(set(new) - set(old), {LUA, XML})
        self.assertEqual({n for n in old if old[n] != new[n]}, set(FILES))
        for name, digest in new.items():
            if name not in old or old[name] != digest:
                self.assertEqual(sha((frozen / 'source' / name).read_bytes()), digest)

    def test_full_tdk_packages_and_helper_asset_match_native_trial(self):
        members = json.loads((ARCHIVE / 'provenance/package-members.json').read_text())
        for stage in ['initial-source', 'source-rehearsal']:
            folder = ARCHIVE / stage; proof = json.loads((folder / 'source-build.json').read_text())
            for language in ['english', 'chinese']:
                data = json.loads((folder / (language + '.json')).read_text())
                expected = patch(baseline(language), language)
                self.assertEqual(data['formats'], expected['formats'])
                self.assertEqual({a['fileName']: a['contentType'] for a in data['assets']},
                                 {a['fileName']: a['contentType'] for a in expected['assets']})
                self.assertEqual(proof['packages'][language]['asset_sha256'],
                                 {n: d for n, d in members[language].items() if n.startswith('template/assets/')})
                actual_files = {f['fileName']: f['content'] for f in data['files']}
                expected_files = {f['fileName']: f['content'] for f in expected['files']}
                self.assertEqual(actual_files.keys(), expected_files.keys())
                if language == 'english':
                    adaptations = json.loads((folder / 'source-proof.json').read_text()).get('source_adaptations', {})
                    for name, op in adaptations.items():
                        self.assertEqual(actual_files[name].count(op['after']), 1)
                        actual_files[name] = actual_files[name].replace(op['after'], op['before'], 1)
                    self.assertEqual(actual_files, expected_files)
                self.assertNotIn(XML, actual_files)

    def test_original_762_translations_retained_and_only_five_added(self):
        folder = ARCHIVE / 'source-rehearsal'
        delta = json.loads((folder / 'translation-delta.json').read_text())
        ref = json.loads((folder / 'source-proof.json').read_text())['chinese_commit']
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'archive', ref, 'translation/tree'])
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            files = {m.name.removeprefix('translation/'): archive.extractfile(m).read() for m in archive if m.name.endswith('/translation.md')}
        self.assertEqual({n: sha(b) for n, b in files.items()}, delta['original_tree_sha256'])
        old = Counter(pair(b.decode()) for b in files.values()); self.assertEqual(sum(old.values()), 762)
        reviewed = {str(p.relative_to(folder / 'reviewed')): p for p in (folder / 'reviewed').rglob('translation.md')}
        self.assertEqual(len(reviewed), 10)
        for name, p in reviewed.items(): self.assertEqual(sha(p.read_bytes()), delta['reviewed_tree_sha256'][name])
        extra = Counter(pair(p.read_text()) for p in reviewed.values())
        for source, target in delta['duplicate_recovery'].items():
            self.assertEqual({v for s, v in old if s == source}, {target})
            extra.pop((source, target))
        self.assertEqual(extra, Counter(map(tuple, delta['added'])))
        self.assertEqual((delta['before_units'], delta['retained_pairs'], delta['after_units']), (762, 762, 767))
        self.assertEqual(delta['removed'], [])

    def test_all_3312_bilingual_layout_and_mode_cases_reproduce(self):
        frozen = ARCHIVE / 'source-rehearsal'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); build = root / 'build'; build.mkdir()
            # Test-only source carriers, not native or release packages. The
            # complete actual asset/member receipts are verified separately.
            for language in ['english', 'chinese']:
                with zipfile.ZipFile(build / (language + '.zip'), 'w') as z:
                    z.writestr('template/template.json', (frozen / (language + '.json')).read_bytes())
            result = compare_sources(build, english_root(), root / 'comparison')
        proof = json.loads((frozen / 'parity.json').read_text())
        self.assertTrue(result['passed']); self.assertEqual(len(result['rows']), 3312)
        # Absolute checkout paths can change fixture enumeration order in CI;
        # retain every complete row (including duplicates), not that order.
        canonical_rows = lambda rows: sorted(json.dumps(row, sort_keys=True) for row in rows)
        self.assertEqual(canonical_rows(result['rows']), canonical_rows(proof['rows']))
        self.assertFalse(proof['native_rebuilt_source_checked'])

    def test_existing_translator_rebuilds_adapted_q9_q15_without_xml_units(self):
        from dsw_document_template_tool.template_transform import expand_template_dir
        from dsw_document_template_tool.translation_tree import export_translation_tree, merge_translation_tree, sync_translation_tree
        from dsw_document_template_tool._translation_tree.document import parse_translation_document, parse_sentence_text
        from dsw_document_template_tool._translation_tree.manifest import load_tree_manifest
        frozen = ARCHIVE / 'source-rehearsal'
        proof = json.loads((frozen / 'source-proof.json').read_text())
        delta = json.loads((frozen / 'translation-delta.json').read_text())
        translations = dict(delta['added']); translations.update(delta['duplicate_recovery'])
        names = list(proof['source_adaptations']) + [LUA, XML]
        actual = {f['fileName']: f['content'] for f in json.loads((frozen / 'chinese.json').read_text())['files']}
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'archive', proof['chinese_commit'], 'translation'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with tarfile.open(fileobj=io.BytesIO(raw)) as archive: archive.extractall(root / 'prior', filter='data')
            source = root / 'source'; source.mkdir()
            (source / 'template.json').write_bytes((frozen / 'source/template.json').read_bytes())
            for name in names:
                path = source / name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((frozen / 'source' / name).read_bytes())
            expanded, fresh, merged, translated = [root / n for n in ['expanded', 'fresh', 'merged', 'translated']]
            expand_template_dir(source_dir=source, output_dir=expanded, profile='science-europe')
            export_translation_tree(source_dir=expanded, output_dir=fresh, source_lang='en', target_lang='zh_Hant')
            merge_translation_tree(old_tree_dir=root / 'prior/translation', new_tree_dir=fresh, output_dir=merged,
                                   source_lang='en', target_lang='zh_Hant')
            units = load_tree_manifest(merged)['units']
            self.assertFalse(any(u['source_file'] in [LUA, XML] for u in units))
            for unit in units:
                path = merged / unit['document_path']
                if parse_translation_document(document_path=path, source_lang='en', target_lang='zh_Hant').strip(): continue
                sentence = parse_sentence_text(document_path=path, source_lang='en')
                self.assertIn(sentence, translations)
                text = path.read_text(); self.assertEqual(text.count('~~~jinja\n\n~~~'), 1)
                path.write_text(text.replace('~~~jinja\n\n~~~', '~~~jinja\n' + translations[sentence] + '\n~~~', 1))
            sync_translation_tree(tree_dir=merged, source_dir=expanded, output_dir=translated, source_lang='en', target_lang='zh_Hant')
            for name in proof['source_adaptations']: self.assertEqual((translated / name).read_text(), actual[name])
            for name in [LUA, XML]: self.assertEqual((translated / name).read_bytes(), (source / name).read_bytes())

    def test_initial_102_failures_are_not_reclassified_as_passes(self):
        folder = ARCHIVE / 'initial-source'; proof = json.loads((folder / 'parity.json').read_text())
        self.assertFalse(proof['passed']); self.assertEqual(len(proof['rows']), 3312)
        failures = [r for r in proof['rows'] if not r['passed']]
        self.assertEqual(len(failures), 102); self.assertEqual({r['language'] for r in failures}, {'chinese'})
        self.assertTrue(all(not r['dom_identical'] for r in failures))
        review = (folder / 'examples/chinese-False-html-review.diff').read_text()
        submit = (folder / 'examples/chinese-False-html-submission.diff').read_text()
        self.assertIn('（計畫名稱尚未提供） - 0 </strong>', review)
        self.assertIn('即「個人資料」。 我們使用', submit)
        for name, key, module in [('source-proof.json', 'source_script_sha256', 'source_rehearsal.py'),
                                  ('source-build.json', 'checker_sha256', 'source_finish.py')]:
            self.assertEqual(json.loads((folder / name).read_text())[key], sha((folder / 'reproduce' / module).read_bytes()))


if __name__ == '__main__': unittest.main()
