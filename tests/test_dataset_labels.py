import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-dataset-labels'
sys.path.insert(0, str(ROOT / 'experiments/dataset-labels'))
from label_recipe import patch, LABELS
from label_probe import compare, expected_order, replies_from
from notice_recipe import project as reverse


def english_root():
    return next(p for p in [ROOT.parent / 'english', ROOT.parent / 'science-europe-template'] if (p / 'scripts/output_profile_contract.py').is_file())


class DatasetLabelTests(unittest.TestCase):
    def test_recipe_is_exactly_reversible_and_only_changes_classified_fallbacks(self):
        for language in ['english', 'chinese']:
            original = json.loads((ROOT / 'reviews/2026-09-21-submission-polish/package' / ('before-' + language + '.json')).read_text())
            changed, operations = patch(original, language)
            self.assertEqual(sum(len(v) for v in operations['labels'].values()), 15)
            value = changed
            for layer in ['labels', 'polish', 'marked']: value = reverse(value, operations[layer])
            self.assertEqual(value, original)
            for name in original:
                if name != 'files': self.assertEqual(original[name], changed[name])

    def test_actual_names_and_authored_label_markup_are_not_replaced(self):
        english = english_root(); sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
        from output_profile_contract import environment, WRAPPER
        from generate_pilot_fixtures import IDS
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            original = json.loads((ROOT / 'reviews/2026-09-21-submission-polish/package' / ('before-' + language + '.json')).read_text())
            changed, _ = patch(original, language)
            for escape in [False, True]:
                templates = [environment(english, escape, {f['fileName']: f['content'] for f in d['files']}).from_string(WRAPPER) for d in [original, changed]]
                for name in ['N/A', '(no name given)', '（名稱尚未提供）', 'Instrument dataset 1', '儀器資料集 1']:
                    replies = replies_from(english / 'fixtures/pilot' / locale / 'profile-partial.events.json')
                    field = next(p for p in replies if p.endswith(IDS['measuredDataNameQUuid']))
                    replies[field] = name
                    authored = next(p for p, value in replies.items() if isinstance(value, str) and 'Original.csv' in value)
                    replies[authored] += '<span class="dataset-label" data-list-kind="authored" data-list-index="999">AUTHORED-LABEL: N/A</span>'
                    self.assertEqual(*[t.render(repliesMap=replies) for t in templates])
                    old, new = [BeautifulSoup(t.render(repliesMap=replies, output_profile='submission'), 'html.parser') for t in templates]
                    compare(old, new, language, replies)
                    self.assertIn(name, new.select_one('#q-how-data').get_text())
                    self.assertTrue(new.select('.answer-detail .dataset-label[data-list-kind="authored"]'))

    def test_frozen_checksums_and_explicit_acceptance_limits(self):
        self.assertEqual(hashlib.sha256((ARCHIVE / 'checksums.json').read_bytes()).hexdigest(), 'c81445f317934ec5c3902d71a293f89034e4aa6980cc9104759973da976cd45a')
        checksums = json.loads((ARCHIVE / 'checksums.json').read_text())
        self.assertEqual(set(checksums), {str(p.relative_to(ARCHIVE)) for p in ARCHIVE.rglob('*') if p.is_file() and p.name != 'checksums.json'})
        for name, expected in checksums.items(): self.assertEqual(hashlib.sha256((ARCHIVE / name).read_bytes()).hexdigest(), expected, name)
        inventory = json.loads((ARCHIVE / 'inventory.json').read_text())
        for key in ['source_repo_modified', 'translation_tree_modified', 'global_switch_complete', 'release_acceptance', 'microsoft_word_acceptance']:
            self.assertFalse(inventory[key])
        proof = json.loads((ARCHIVE / 'provenance/structural.json').read_text())
        self.assertTrue(proof['passed']); self.assertEqual(len(proof['rows']), 528)

    def test_all_native_pairs_and_original_filtered_numbering(self):
        from label_native import run
        rows = run(ARCHIVE / 'before', ARCHIVE / 'after', ARCHIVE / 'fixtures', english_root(), compacted=True)
        expected = json.loads((ARCHIVE / 'provenance/native.json').read_text())['rows']
        for row in rows:
            receipt = json.loads((ARCHIVE / 'after/renders' / ('dataset-labels-' + row['profile'] + '-' + row['language'] + '.html.compact.json')).read_text())
            self.assertEqual(row['artifacts']['html'], receipt['compact_html_sha256'])
            row['artifacts']['html'] = receipt['original_html_sha256']
        self.assertEqual(json.loads(json.dumps(rows)), expected)
        from output_profile_contract import expected as partial
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            replies = replies_from(ARCHIVE / 'fixtures' / locale / 'dataset-labels.events.json')
            before = partial(BeautifulSoup((ARCHIVE / 'before/renders' / ('dataset-labels-' + language + '.html')).read_text(), 'html.parser'), language)
            after = BeautifulSoup((ARCHIVE / 'after/renders' / ('dataset-labels-submission-' + language + '.html')).read_text(), 'html.parser')
            self.assertEqual({n['data-list-kind'] for n in after.select('.dataset-label')}, set(LABELS[language]))
            reference = after.select('#q-copyright-ipr .dataset-label[data-list-kind="reference"]')
            self.assertEqual([n['data-list-index'] for n in reference], ['2'])
            broken = copy.deepcopy(after)
            node = broken.select_one('#q-copyright-ipr .dataset-label[data-list-kind="reference"]')
            node['data-list-index'] = '1'; node.string = LABELS[language]['reference'] + ' 1'
            with self.assertRaises(AssertionError): compare(before, broken, language, replies)

    def test_native_source_receipts_and_cleanup(self):
        for language in ['english', 'chinese']:
            before, after = [json.loads((ARCHIVE / 'package' / (phase + '-' + language + '.json')).read_text()) for phase in ['before', 'after']]
            self.assertEqual(patch(before, language)[0], after)
            members = json.loads((ARCHIVE / 'provenance/package-members.json').read_text())
            self.assertEqual(set(members['before'][language]), set(members['after'][language]))
            self.assertEqual({name for name, digest in members['before'][language].items() if members['after'][language][name] != digest}, {'template/template.json'})
        for phase in ['before', 'after', 'superseded']:
            cleanup = json.loads((ARCHIVE / 'provenance' / (phase + '-owned-test-template-cleanup.json')).read_text())
            self.assertEqual(len(cleanup['deleted']), 2)
            self.assertEqual((cleanup['project_references'], cleanup['document_references']), (0, 0))


if __name__ == '__main__': unittest.main()
