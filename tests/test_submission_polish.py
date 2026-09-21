import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-submission-polish'
sys.path[:0] = [str(ROOT / 'experiments/submission-polish'), str(ROOT / 'experiments/submission-notices')]
from polish_recipe import patch
from polish_probe import compare, replies_from
from notice_recipe import project as reverse


def english_root():
    return next(p for p in [ROOT.parent / 'english', ROOT.parent / 'science-europe-template'] if (p / 'scripts/output_profile_contract.py').is_file())


class SubmissionPolishSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.english = english_root()
        sys.path[:0] = [str(cls.english / 'scripts'), str(cls.english / 'tests')]
        from output_profile_contract import environment, WRAPPER
        cls.templates = {}
        for language in ['english', 'chinese']:
            before = json.loads((ROOT / 'reviews/2026-09-21-submission-notices/package' / ('before-' + language + '.json')).read_text())
            after, operations = patch(before, language)
            for escape in [False, True]:
                cls.templates[language, escape] = [environment(cls.english, escape, {f['fileName']: f['content'] for f in data['files']}).from_string(WRAPPER + "{% include 'src/contributors.html.j2' %}") for data in [before, after]]

    def render_pair(self, language, escape, replies):
        def render(template, **kw):
            return template.render(repliesMap=replies, dc=SimpleNamespace(project=SimpleNamespace(created_by=None), e=SimpleNamespace(choices={})), **kw)
        templates = self.templates[language, escape]
        reviews = [render(t) for t in templates]
        self.assertEqual(*reviews)
        for mode in ['review', 'unknown']:
            self.assertEqual(render(templates[1], output_profile=mode), reviews[0])
        old, new = [BeautifulSoup(render(t, output_profile='submission'), 'html.parser') for t in templates]
        compare(old, new, language, replies)
        return old, new

    def test_only_four_additional_sources_and_exact_inverse(self):
        for language in ['english', 'chinese']:
            before = json.loads((ROOT / 'reviews/2026-09-21-submission-notices/package' / ('before-' + language + '.json')).read_text())
            after, ops = patch(before, language)
            self.assertEqual(set(ops['polish']), {'src/projects.html.j2', 'src/contributors.html.j2', 'src/questions/01-how-data.html.j2', 'src/quality-control.html.j2'})
            self.assertEqual(reverse(reverse(after, ops['polish']), ops['marked']), before)
            for key in before:
                if key != 'files': self.assertEqual(before[key], after[key])
            broken = copy.deepcopy(after)
            file = next(f for f in broken['files'] if f['fileName'] == 'src/projects.html.j2')
            file['content'] = file['content'].replace('projectNumber or', 'false or', 1)
            with self.assertRaises(AssertionError): reverse(broken, ops['polish'])

    def test_absent_fields_are_not_literal_na_zero_or_warning_text(self):
        from generate_pilot_fixtures import IDS, path
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            base = replies_from(self.english / 'fixtures/pilot' / locale / 'profile-partial.events.json')
            projects = path('adminDetailsCUuid', 'projectsQUuid'); prefix = path(projects, base[projects][0])
            fields = ['projectNumberQUuid', 'projectStartQUuid', 'projectEndQUuid']
            for escaping in [False, True]:
                for field in fields:
                    for value in [None, '', 'N/A', '0', '尚未提供', 'Information not provided']:
                        replies = copy.deepcopy(base)
                        if value is None: replies.pop(path(prefix, field), None)
                        else: replies[path(prefix, field)] = value
                        old, new = self.render_pair(language, escaping, replies)
                        if value:
                            self.assertIn(value, new.select_one('#dmp-projects').get_text())
                        else:
                            self.assertLess(len(new.select('#dmp-projects tr')), len(old.select('#dmp-projects tr')))

    def test_quality_free_answers_and_no_or_unknown_choices_stay_unchanged(self):
        from generate_pilot_fixtures import IDS, path
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            base = replies_from(self.english / 'fixtures/pilot' / locale / 'profile-partial.events.json')
            quality = next(p for p in base if p.endswith(IDS['measuredDataQualityQUuid']))
            other = path(quality, 'measuredDataQualityYesAUuid', 'mdQualityOtherQUuid')
            for escaping in [False, True]:
                for answer in [None, 'unknown', IDS['mdQualityOtherNoAUuid'], IDS['mdQualityOtherYesAUuid']]:
                    for text in ['', '<p>尚待補充：Original.csv / N/A / 0.</p><p>Second paragraph.</p>']:
                        replies = copy.deepcopy(base)
                        replies[quality] = IDS['measuredDataQualityYesAUuid']
                        if answer is None: replies.pop(other, None)
                        else: replies[other] = answer
                        replies[path(other, 'mdQualityOtherYesAUuid', 'mdQualityOtherWhatQUuid')] = text
                        self.render_pair(language, escaping, replies)
                for choice in [IDS['measuredDataQualityNoAUuid'], 'unknown', '']:
                    replies = copy.deepcopy(base); replies[quality] = choice
                    old, new = self.render_pair(language, escaping, replies)
                    if choice == IDS['measuredDataQualityNoAUuid']:
                        self.assertTrue(new.select('[data-fact-id="quality-control"][data-status="explicit-no"]'))

    def test_missing_grant_retains_funder_status_and_authored_lookalikes(self):
        from generate_pilot_fixtures import IDS, path
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            base = replies_from(self.english / 'fixtures/pilot' / locale / 'profile-partial.events.json')
            projects = path('adminDetailsCUuid', 'projectsQUuid'); project = path(projects, base[projects][0])
            funders = path(project, 'fundersQUuid'); item = '00000000-0000-4000-8000-000000000001'
            base[funders] = [item]; prefix = path(funders, item)
            label = 'Funder: grant number not yet given' if language == 'english' else '機構：尚未提供補助編號'
            for escaping in [False, True]:
                for named in [False, True]:
                    for grant in [None, 'N/A', '0', 'grant number not yet given']:
                        replies = copy.deepcopy(base)
                        if named: replies[path(prefix, 'funderNameQUuid')] = {'value': {'value': {'type': 'PlainType', 'value': label}}}
                        if grant is not None: replies[path(prefix, 'grantNumberQUuid')] = grant
                        replies[path(prefix, 'funderStatusQUuid')] = IDS['funderStatusRejectedAUuid']
                        old, new = self.render_pair(language, escaping, replies)
                        entry = new.select_one('#dmp-projects .project-details li').get_text()
                        self.assertIn('(rejected)' if language == 'english' else '（未核准）', entry)
                        if named: self.assertIn(label, entry)
                        if grant: self.assertIn(grant, entry)
                        if not named: self.assertFalse(entry.startswith((':', '：')))


class SubmissionPolishArchiveTests(unittest.TestCase):
    def test_sealed_inventory_and_limits(self):
        self.assertEqual(hashlib.sha256((ARCHIVE / 'checksums.json').read_bytes()).hexdigest(), '8005c0c66c6ad34582ca43b0e6fdba67045dee7d0b3894bd71ffba144771adf6')
        checksums = json.loads((ARCHIVE / 'checksums.json').read_text())
        self.assertEqual(set(checksums), {str(p.relative_to(ARCHIVE)) for p in ARCHIVE.rglob('*') if p.is_file() and p.name != 'checksums.json'})
        for name, digest in checksums.items(): self.assertEqual(hashlib.sha256((ARCHIVE / name).read_bytes()).hexdigest(), digest, name)
        inventory = json.loads((ARCHIVE / 'inventory.json').read_text())
        for key in ['release_acceptance', 'source_repo_modified', 'translation_tree_modified', 'global_switch_complete', 'microsoft_word_acceptance']:
            self.assertFalse(inventory[key])
        self.assertEqual(inventory['structural_cases'], 780)
        structural = json.loads((ARCHIVE / 'provenance/structural.json').read_text())
        self.assertTrue(structural['passed']); self.assertEqual(len(structural['rows']), 780)

    def test_native_pairs_recompute_and_reject_lost_authored_answers(self):
        from polish_native import run
        rows = run(ARCHIVE / 'before', ARCHIVE / 'after', ARCHIVE / 'fixtures', english_root(), compacted=True)
        original = json.loads((ARCHIVE / 'provenance/native.json').read_text())['rows']
        for row in rows:
            stem = '-'.join([row['case'], row['profile'], row['language']])
            receipt = json.loads((ARCHIVE / 'after/renders' / (stem + '.html.compact.json')).read_text())
            self.assertEqual(row['artifacts']['html'], receipt['compact_html_sha256'])
            row['artifacts']['html'] = receipt['original_html_sha256']
        self.assertEqual(json.loads(json.dumps(rows)), original)
        from output_profile_contract import expected as partial
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            old = partial(BeautifulSoup((ARCHIVE / 'before/renders' / ('submission-metadata-' + language + '.html')).read_text(), 'html.parser'), language)
            new = BeautifulSoup((ARCHIVE / 'after/renders' / ('submission-metadata-submission-' + language + '.html')).read_text(), 'html.parser')
            replies = replies_from(ARCHIVE / 'fixtures' / locale / 'submission-metadata.events.json')
            for selector in ['.answer-detail .data-gap', '.abstract', 'p[data-fact-id="quality-other"]']:
                broken = copy.deepcopy(new); node = broken.select_one(selector); self.assertIsNotNone(node); node.decompose()
                with self.assertRaises(AssertionError): compare(old, broken, language, replies)

    def test_native_packages_match_reversible_recipe_and_cleanup_is_scoped(self):
        for language in ['english', 'chinese']:
            before, after = [json.loads((ARCHIVE / 'package' / (phase + '-' + language + '.json')).read_text()) for phase in ['before', 'after']]
            actual, _ = patch(before, language); self.assertEqual(actual, after)
        for phase in ['before', 'after']:
            receipt = json.loads((ARCHIVE / 'provenance' / (phase + '-owned-test-template-cleanup.json')).read_text())
            self.assertEqual(len(receipt['deleted']), 2)
            self.assertEqual((receipt['project_references'], receipt['document_references']), (0, 0))
        lifecycle = json.loads((ARCHIVE / 'provenance/worker-lifecycle.json').read_text())
        self.assertEqual(lifecycle['deleted_owned_templates'], 4)
        self.assertTrue(lifecycle['stock_worker_restored'])
        self.assertTrue(all(r['status'] == 'exited' for r in lifecycle['after']))

    def test_compacted_html_restores_original_fonts_and_bytes(self):
        from importlib.resources import files
        sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
        from compact import restore_source
        font = files('dsw_document_template_tool').joinpath('resources/fonts/NotoSansTC-Variable.ttf').read_bytes()
        digest = hashlib.sha256(font).hexdigest()
        paths = list(ARCHIVE.glob('*/renders/*.html')); self.assertEqual(len(paths), 18)
        for path in paths:
            receipt = json.loads(path.with_suffix('.html.compact.json').read_text())
            self.assertEqual(hashlib.sha256(restore_source(path.read_bytes(), {digest: font})).hexdigest(), receipt['original_html_sha256'])


if __name__ == '__main__': unittest.main()
