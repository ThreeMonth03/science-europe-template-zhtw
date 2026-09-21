import copy
import itertools
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'experiments/table-flow'), str(ROOT / 'experiments/ethics-prompts'),
               str(ROOT / 'experiments/entity-labels'), str(ROOT / 'scripts')]
from budget_recipe import baseline, patch, TARGET
from budget_probe import templates, check_case, compare
from ethics_trial import fixture_events
from entity_recipe import reverse


def english_root():
    return next(p for p in [ROOT.parent / 'english', ROOT.parent / 'science-europe-template']
                if (p / 'scripts/output_profile_contract.py').is_file())


class EmptyBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.english = english_root(); sys.path[:0] = [str(cls.english / 'scripts'), str(cls.english / 'tests')]
        cls.pairs = {(lang, escape, layout): templates(cls.english, lang, escape, layout)
                     for lang in ['english', 'chinese'] for escape in [False, True] for layout in ['html', 'pdf', 'word']}

    def replies(self, language):
        return {e['path']: e['value']['value'] for e in fixture_events(self.english,
                'en' if language == 'english' else 'zh-Hant', 'ethics-missing')}

    def test_three_reversible_edits_one_file_no_assets_versions_or_translations_changed(self):
        for language in ['english', 'chinese']:
            old = baseline(language); new, operations = patch(old, language)
            self.assertEqual(set(operations), {TARGET}); self.assertEqual(len(operations[TARGET]), 3)
            self.assertEqual(reverse(new, operations), old)
            self.assertEqual({k: v for k, v in old.items() if k != 'files'}, {k: v for k, v in new.items() if k != 'files'})
            bad = copy.deepcopy(old); bad['files'][0]['content'] += ' '
            with self.assertRaises(AssertionError): patch(bad, language)

    def test_all_budget_presence_combinations_keep_original_project_numbering_and_tables(self):
        from generate_pilot_fixtures import path
        base = path('adminDetailsCUuid', 'projectsQUuid')
        for (language, escape, layout), pair in self.pairs.items():
            for flags in itertools.product([False, True], repeat=3):
                with self.subTest(language=language, escape=escape, layout=layout, flags=flags):
                    replies = self.replies(language); items = replies[base]; self.assertEqual(len(items), 3)
                    for item, keep in zip(items, flags):
                        cost = path(base, item, 'costQUuid')
                        # An existing but completely unanswered cost item stays.
                        replies[cost] = ['00000000-0000-0000-0000-000000000123'] if keep else []
                    before, after, changes = check_case(pair, replies)
                    groups = after.select('#q-required-resources > .answer > .project-resources')
                    self.assertEqual([g['data-item-id'] for g in groups], [path(base, item) for item, keep in zip(items, flags) if keep])
                    self.assertEqual(len(changes), flags.count(False) + (not any(flags)))
                    self.assertEqual(len(after.select('#q-required-resources > .answer > h4')), int(any(flags)))
                    for group in groups:
                        original = next(g for g in before.select('.project-resources') if g['data-item-id'] == group['data-item-id'])
                        self.assertEqual(str(group), str(original))

    def test_zero_one_and_unreachable_cost_replies_never_create_empty_heading(self):
        from generate_pilot_fixtures import path
        base = path('adminDetailsCUuid', 'projectsQUuid')
        for (language, escape, layout), pair in self.pairs.items():
            for count in [0, 1]:
                replies = self.replies(language); replies[base] = replies[base][:count]
                for item in replies[base]: replies.pop(path(base, item, 'costQUuid'), None)
                _, after, changes = check_case(pair, replies)
                self.assertFalse(after.select('#q-required-resources > .answer > h4, #q-required-resources .project-resources'))
                self.assertEqual(len(changes), 2 if count else 0)

    def test_nonempty_literal_names_zero_budget_links_and_authored_lookalikes_survive(self):
        from generate_pilot_fixtures import path
        base = path('adminDetailsCUuid', 'projectsQUuid')
        answer = '<p class="project-resources">N/A / 0 / Original.csv. Information not provided:</p><p><a href="https://example.org/budget">Budget</a>，。！</p>'
        for (language, escape, layout), pair in self.pairs.items():
            replies = self.replies(language); item = replies[base][-1]
            replies[path(base, item, 'projectNameQUuid')] = 'N/A'
            costs = path(base, item, 'costQUuid'); cost = replies[costs][0]
            replies[path(costs, cost, 'costDescriptionQUuid')] = answer
            replies[path(costs, cost, 'costAmountQUuid')] = '0'
            before, after, _ = check_case(pair, replies)
            direct = '#q-required-resources > .answer > .project-resources'
            old = before.select(direct)[-1]; new = after.select(direct)[-1]
            self.assertEqual(str(old), str(new)); self.assertIn('Original.csv.', new.get_text())
            self.assertEqual(len(new.select('a[href="https://example.org/budget"]')), 1)

    def test_oracle_rejects_numbering_authored_loss_empty_heading_and_overview_change(self):
        for language in ['english', 'chinese']:
            pair = self.pairs[language, False, 'html']; replies = self.replies(language)
            before, after, _ = check_case(pair, replies)
            for mutation in ['name', 'authored', 'group', 'overview', 'reinsert']:
                broken = copy.deepcopy(after)
                groups = broken.select('#q-required-resources > .answer > .project-resources')
                if mutation == 'name': groups[0].select_one('p > strong').string = 'Project 1'
                elif mutation == 'authored': groups[0].select_one('table td').decompose()
                elif mutation == 'group': groups[-1].decompose()
                elif mutation == 'overview': broken.select_one('#q-ethical-issues').decompose()
                else: groups[0].insert_before(copy.deepcopy(before.select_one('#q-required-resources > .answer > .project-resources')))
                with self.assertRaises(AssertionError): compare(before, broken, replies)


if __name__ == '__main__': unittest.main()
