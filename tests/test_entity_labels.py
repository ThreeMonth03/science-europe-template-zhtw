import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'experiments/entity-labels'), str(ROOT / 'scripts')]
from entity_recipe import baseline, patch, reverse, LABELS
from entity_probe import templates, check_case, compare
from entity_trial import fixture_events


def english_root():
    return next(p for p in [ROOT.parent / 'english', ROOT.parent / 'science-europe-template']
                if (p / 'scripts/output_profile_contract.py').is_file())


class EntityLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.english = english_root()
        sys.path[:0] = [str(cls.english / 'scripts'), str(cls.english / 'tests')]

    def replies(self, locale):
        return {e['path']: e['value']['value'] for e in fixture_events(self.english, locale)}

    def test_exact_five_file_reversible_recipe_without_asset_or_metadata_change(self):
        for language in LABELS:
            old = baseline(language); new, operations = patch(old, language)
            self.assertEqual(reverse(new, operations), old)
            self.assertEqual(len(operations), 5)
            self.assertEqual(sum(map(len, operations.values())), 7)
            self.assertEqual({k: v for k, v in old.items() if k != 'files'},
                             {k: v for k, v in new.items() if k != 'files'})
            for file in old['files']:
                if file['fileName'] not in operations:
                    self.assertIn(file, new['files'])
            broken = copy.deepcopy(old); broken['files'][0]['content'] += ' '
            with self.assertRaises(AssertionError): patch(broken, language)

    def test_filtered_project_identity_nested_lists_and_review_bytes(self):
        from generate_pilot_fixtures import path
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            replies = self.replies(locale)
            for escape in [False, True]:
                for word in [False, True]:
                    pair = templates(self.english, language, escape, word)
                    old, new, changes = check_case(pair, replies, language)
                    ethical = new.select('#q-ethical-issues .ethical-project > strong')
                    self.assertEqual([n.get_text() for n in ethical],
                                     [LABELS[language]['project'] + ' 2', LABELS[language]['project'] + ' 3'])
                    self.assertEqual([c['index'] for c in changes if c['kind'] == 'resource'], [2, 2])
                    self.assertEqual([c['index'] for c in changes if c['kind'] == 'software'], [2, 2])
                    self.assertEqual(len({c['identity'] for c in changes if c['kind'] == 'resource'}), 2)
                    self.assertEqual(len({c['identity'] for c in changes if c['kind'] == 'software'}), 2)
                    # Original order is the source of identity, even after an
                    # actual questionnaire reorder. It is not a permanent ID.
                    reordered = copy.deepcopy(replies)
                    p = path('adminDetailsCUuid', 'projectsQUuid'); reordered[p].reverse()
                    _, changed, _ = check_case(pair, reordered, language)
                    self.assertEqual([n.get_text() for n in changed.select('#q-ethical-issues .ethical-project > strong')],
                                     [LABELS[language]['project'] + ' 1', LABELS[language]['project'] + ' 2'])

    def test_authored_placeholder_names_and_markup_remain_literal(self):
        from generate_pilot_fixtures import IDS
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            replies = self.replies(locale)
            name_fields = {IDS[n] for n in ['projectNameQUuid', 'costTitleQUuid', 'publishedSpecSwUseWhatNameQUuid']}
            for name in ['N/A', '0', '(no name given)', '（名稱尚未提供）', 'Project 2', '計畫 2']:
                variant = copy.deepcopy(replies)
                for key in list(variant):
                    if key.split('.')[-1] in name_fields: variant[key] = name
                authored = next(p for p in variant if p.endswith(IDS['costDescriptionQUuid']))
                marker = '<span class="entity-label" data-list-index="999">AUTHORED: (no name given) / 尚待補充 / 0 / Original.csv.</span>'
                variant[authored] += marker
                for escape in [False, True]:
                    pair = templates(self.english, language, escape)
                    _, new, _ = check_case(pair, variant, language)
                    self.assertIn(marker, str(new))
                    self.assertIn(name, new.get_text())

    def test_oracle_rejects_wrong_number_owner_fact_and_punctuation(self):
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            replies = self.replies(locale)
            old, new, _ = check_case(templates(self.english, language, False), replies, language)
            for selector, replacement in [
                ('#q-ethical-issues .ethical-project > strong', LABELS[language]['project'] + ' 1'),
                ('#q-access-data .dataset-section > ul > li:nth-of-type(2) > strong', LABELS[language]['software'] + ' 1'),
                ('#q-required-resources .answer-detail', 'LOST-AUTHORED-FACT'),
            ]:
                broken = copy.deepcopy(new); broken.select_one(selector).string = replacement
                with self.assertRaises(AssertionError): compare(old, broken, language, replies)
            broken = copy.deepcopy(new)
            node = broken.select_one('#q-required-resources .project-resources')
            node['data-item-id'] = 'wrong-owner'
            with self.assertRaises(AssertionError): compare(old, broken, language, replies)
            broken = copy.deepcopy(new); broken.select_one('#q-ethical-issues p').append('.')
            with self.assertRaises(AssertionError): compare(old, broken, language, replies)


if __name__ == '__main__': unittest.main()
