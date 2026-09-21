import copy
import itertools
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'experiments/ethics-prompts'), str(ROOT / 'experiments/entity-labels'), str(ROOT / 'scripts')]
from ethics_recipe import baseline, patch, TARGET, TEXT
from ethics_probe import templates, check_case, compare
from ethics_trial import fixture_events
from entity_recipe import reverse


def english_root():
    return next(p for p in [ROOT.parent / 'english', ROOT.parent / 'science-europe-template']
                if (p / 'scripts/output_profile_contract.py').is_file())


class EthicsPromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.english = english_root(); sys.path[:0] = [str(cls.english / 'scripts'), str(cls.english / 'tests')]
        cls.pairs = {(lang, escape, word): templates(cls.english, lang, escape, word)
                     for lang in TEXT for escape in [False, True] for word in [False, True]}

    def replies(self, language, case='ethics-missing'):
        locale = 'en' if language == 'english' else 'zh-Hant'
        return {e['path']: e['value']['value'] for e in fixture_events(self.english, locale, case)}

    def test_two_edits_in_one_file_and_reversible_review_recipe(self):
        for language in TEXT:
            old = baseline(language); new, operations = patch(old, language)
            self.assertEqual(set(operations), {TARGET}); self.assertEqual(len(operations[TARGET]), 2)
            self.assertEqual(reverse(new, operations), old)
            self.assertEqual({k: v for k, v in old.items() if k != 'files'},
                             {k: v for k, v in new.items() if k != 'files'})
            broken = copy.deepcopy(old); broken['files'][0]['content'] += ' '
            with self.assertRaises(AssertionError): patch(broken, language)

    def test_all_nine_personal_sensitive_states_keep_explicit_facts(self):
        from generate_pilot_fixtures import IDS, path
        produced = path('preservingCUuid', 'producedDataQUuid')
        for (language, escape, word), pair in self.pairs.items():
            for personal, sensitive in itertools.product([None, 'Yes', 'No'], repeat=2):
                replies = self.replies(language); item = replies[produced][0]
                for field, choice in [('containPersonal', personal), ('containSensitive', sensitive)]:
                    if choice: replies[path(produced, item, field + 'QUuid')] = IDS[field + choice + 'AUuid']
                before, after, changes = check_case(pair, replies, language)
                expected = 2 if personal is None and sensitive is None else 1
                self.assertEqual(sum(c['kind'] == 'missing-data-flags' for c in changes), expected)
                self.assertEqual(sum(c['kind'] == 'other-basis-partial-fact' for c in changes), 1)
                self.assertEqual([n.get_text() for n in before.select('.ethical-data-flags')],
                                 [n.get_text() for n in after.select('.ethical-data-flags')])

    def test_alternative_basis_matrix_and_inactive_parent_preserve_authored_text(self):
        from generate_pilot_fixtures import IDS, path
        personal = path('creatingCUuid', 'collectPersonalQUuid')
        gdpr = path(personal, 'collectPersonalYesAUuid', 'cpersGdprQUuid')
        legal = path(gdpr, 'cpersGdprExploreAUuid', 'cpersGdprLegalBasisQUuid')
        other = path(legal, 'cpersGdprLegalBasisOtherAUuid', 'cpersGdprLegalBasisOtherWhichQUuid')
        for (language, escape, word), pair in self.pairs.items():
            for state in ['missing', 'Contract', 'Legit', 'Vital', 'Legal', 'Public', 'Ask', 'unselected']:
                replies = self.replies(language)
                if state in ['Contract', 'Legit', 'Vital', 'Legal']:
                    replies[other] = IDS['cpersGdprLegalBasisOtherWhich' + state + 'AUuid']
                elif state in ['Public', 'Ask']: replies[legal] = IDS['cpersGdprLegalBasis' + state + 'AUuid']
                elif state == 'unselected': del replies[legal]
                before, after, changes = check_case(pair, replies, language)
                self.assertEqual(sum(c['kind'] == 'other-basis-partial-fact' for c in changes), int(state == 'missing'))
                self.assertEqual(before.get_text().count(TEXT[language]['old']) - after.get_text().count(TEXT[language]['old']),
                                 int(state == 'missing'))
                self.assertIn(TEXT[language]['old'], after.get_text())
                self.assertIn(TEXT[language]['flags'], after.select_one('#q-ethical-issues > .answer > .answer-detail').get_text())
                self.assertIn('AUTHORED-PURPOSE: N/A / 0 / Original.csv.', after.get_text())
            # Stale children must not activate a suppressed parent branch.
            for missing in [personal, gdpr]:
                replies = self.replies(language); del replies[missing]
                _, _, changes = check_case(pair, replies, language)
                self.assertFalse(any(c['kind'] == 'other-basis-partial-fact' for c in changes))
            replies = self.replies(language); replies[personal] = IDS['collectPersonalNoAUuid']
            _, _, changes = check_case(pair, replies, language)
            self.assertFalse(any(c['kind'] == 'other-basis-partial-fact' for c in changes))

    def test_answered_control_and_literal_lookalikes_do_not_change(self):
        for (language, escape, word), pair in self.pairs.items():
            replies = self.replies(language, 'ethics-answered')
            before, after, changes = check_case(pair, replies, language)
            self.assertEqual(changes, [])
            self.assertEqual(str(before), str(after))

    def test_identical_authored_sentence_in_same_text_node_is_not_removed(self):
        from generate_pilot_fixtures import path
        purpose = path('creatingCUuid', 'collectPersonalQUuid', 'collectPersonalYesAUuid', 'cpersGdprQUuid',
                       'cpersGdprExploreAUuid', 'cpersGdprPurposeQUuid')
        for (language, escape, word), pair in self.pairs.items():
            replies = self.replies(language)
            replies[purpose] = TEXT[language]['lead'] + ' ' + TEXT[language]['old'] + ' ' + TEXT[language]['flags']
            before, after, _ = check_case(pair, replies, language)
            owned = after.select_one('#q-ethical-issues > .answer > .answer-detail')
            self.assertIn(replies[purpose], owned.get_text())
            self.assertEqual(before.get_text().count(TEXT[language]['old']) - after.get_text().count(TEXT[language]['old']), 1)

    def test_oracle_rejects_fact_removal_false_assurance_and_authored_deletion(self):
        for language in TEXT:
            replies = self.replies(language)
            before, after, _ = check_case(self.pairs[language, False, False], replies, language)
            for replacement in ['', 'All legal requirements have been satisfied.']:
                broken = copy.deepcopy(after)
                node = broken.select_one('#q-ethical-issues > .answer > .answer-detail').contents[0]
                node.replace_with(str(node).replace(TEXT[language]['new'], replacement))
                with self.assertRaises(AssertionError): compare(before, broken, language, replies)
            broken = copy.deepcopy(after)
            broken.select_one('#q-ethical-issues > .answer > .answer-detail p:nth-of-type(2)').decompose()
            with self.assertRaises(AssertionError): compare(before, broken, language, replies)
            broken = copy.deepcopy(after)
            broken.select_one('#q-access-data .dataset-section > ul > li > strong').string = 'LOST-NAME'
            with self.assertRaises(AssertionError): compare(before, broken, language, replies)


if __name__ == '__main__': unittest.main()
