import copy
import itertools
from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'experiments/ethics-lead'), str(ROOT / 'experiments/ethics-prompts'),
               str(ROOT / 'experiments/entity-labels'), str(ROOT / 'scripts')]
from lead_recipe import baseline, patch, TARGET
from lead_probe import templates, check_case, compare, first_reply
from ethics_trial import fixture_events
from entity_recipe import reverse


def english_root():
    return next(p for p in [ROOT.parent / 'english', ROOT.parent / 'science-europe-template']
                if (p / 'scripts/output_profile_contract.py').is_file())


class EthicsLeadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.english = english_root(); sys.path[:0] = [str(cls.english / 'scripts'), str(cls.english / 'tests')]
        cls.pairs = {(lang, escape, word): templates(cls.english, lang, escape, word)
                     for lang in ['english', 'chinese'] for escape in [False, True] for word in [False, True]}

    def replies(self, language):
        return {e['path']: e['value']['value'] for e in fixture_events(self.english,
                'en' if language == 'english' else 'zh-Hant', 'ethics-missing')}

    def test_exact_six_edits_one_file_no_assets_or_version_change(self):
        for language in ['english', 'chinese']:
            old = baseline(language); new, operations = patch(old, language)
            self.assertEqual(set(operations), {TARGET}); self.assertEqual(len(operations[TARGET]), 6)
            self.assertEqual(reverse(new, operations), old)
            self.assertEqual({k: v for k, v in old.items() if k != 'files'}, {k: v for k, v in new.items() if k != 'files'})
            broken = copy.deepcopy(old); broken['files'][0]['content'] += ' '
            with self.assertRaises(AssertionError): patch(broken, language)

    def test_three_authored_boundaries_with_short_long_list_table_and_plain_answers(self):
        from generate_pilot_fixtures import IDS, path
        personal = path('creatingCUuid', 'collectPersonalQUuid')
        gdpr = path(personal, 'collectPersonalYesAUuid', 'cpersGdprQUuid')
        legal = path(gdpr, 'cpersGdprExploreAUuid', 'cpersGdprLegalBasisQUuid')
        fields = [path(legal, 'cpersGdprLegalBasisAskAUuid', name) for name in
                  ['cpersExplainInformedQUuid', 'cpersDescribeProcedureQUuid']]
        fields.append(path(gdpr, 'cpersGdprExploreAUuid', 'cpersGdprPurposeQUuid'))
        answers = ['N/A / 0 / Original.csv. Literal：，。', '<p>Short.</p>',
                   '<p>' + 'Long answer with unchanged punctuation：，。 N/A / 0. ' * 180 + '</p>',
                   '<p>First.</p><p>Second！</p><p>Third？</p>',
                   '<ul><li>First.</li><li>Second！</li></ul>',
                   '<ol><li>First.</li><li>Second！</li></ol>',
                   '<table><thead><tr><th>Item</th><th>Value</th></tr></thead>'
                   '<tbody><tr><td>N/A</td><td>0</td></tr></tbody></table>',
                   '<p class="answer-lead">Authored lookalike.</p><p>Retained.</p>']
        for (language, escape, word), pair in self.pairs.items():
            for key in fields:
                for answer in answers:
                    with self.subTest(language=language, escape=escape, word=word, field=key, answer=answer[:40]):
                        replies = self.replies(language); replies.pop(fields[-1])
                        replies[legal] = IDS['cpersGdprLegalBasisAskAUuid']; replies[key] = answer
                        _, after, changes = check_case(pair, replies, language)
                        self.assertEqual(len(changes), 2); self.assertEqual(changes[-1]['path'], key)
                        lead = after.select_one('#q-ethical-issues > .answer > .answer-detail > p.answer-lead')
                        self.assertNotIn('Authored lookalike.', lead.get_text())
                        self.assertEqual(str(lead.next_sibling), str(BeautifulSoup(answer, 'html.parser').contents[0]))

    def test_only_first_boundary_is_wrapped_and_later_facts_stay_in_order(self):
        from generate_pilot_fixtures import IDS, path
        for (language, escape, word), pair in self.pairs.items():
            replies = self.replies(language)
            gdpr = path('creatingCUuid', 'collectPersonalQUuid', 'collectPersonalYesAUuid', 'cpersGdprQUuid')
            legal = path(gdpr, 'cpersGdprExploreAUuid', 'cpersGdprLegalBasisQUuid')
            replies[legal] = IDS['cpersGdprLegalBasisAskAUuid']
            for field, answer in [('cpersExplainInformedQUuid', '<p>FIRST-ANSWER.</p>'),
                                  ('cpersDescribeProcedureQUuid', '<p>SECOND-ANSWER.</p>')]:
                replies[path(legal, 'cpersGdprLegalBasisAskAUuid', field)] = answer
            replies[path(gdpr, 'cpersGdprExploreAUuid', 'cpersGdprNeedDpiaQUuid')] = IDS['cpersGdprNeedDpiaYesAUuid']
            _, after, changes = check_case(pair, replies, language)
            self.assertEqual(len(changes), 2)
            detail = after.select_one('#q-ethical-issues > .answer > .answer-detail')
            self.assertEqual(len(detail.select(':scope > p.answer-lead')), 1)
            self.assertLess(detail.get_text().index('FIRST-ANSWER.'), detail.get_text().index('SECOND-ANSWER.'))
            self.assertLess(detail.get_text().index('SECOND-ANSWER.'), detail.get_text().index('AUTHORED-PURPOSE:'))

    def test_empty_answer_and_inactive_parent_do_not_create_leads(self):
        from generate_pilot_fixtures import path, IDS
        for (language, escape, word), pair in self.pairs.items():
            replies = self.replies(language); replies.pop(first_reply(replies))
            before, after, changes = check_case(pair, replies, language)
            self.assertEqual([c['kind'] for c in changes], ['release-final-name-only-item'])
            self.assertEqual(before.get_text(), after.get_text())
            replies = self.replies(language)
            replies[path('creatingCUuid', 'collectPersonalQUuid')] = IDS['collectPersonalNoAUuid']
            before, after, changes = check_case(pair, replies, language)
            self.assertEqual([c['kind'] for c in changes], ['release-final-name-only-item'])
            self.assertEqual(before.get_text(), after.get_text())

    def test_oracle_rejects_authored_loss_rewording_and_extra_keep(self):
        for language in ['english', 'chinese']:
            pair = self.pairs[language, False, False]; replies = self.replies(language)
            before, after, _ = check_case(pair, replies, language)
            for mutation in ['delete', 'punctuation', 'whole-keep', 'other-question']:
                broken = copy.deepcopy(after)
                detail = broken.select_one('#q-ethical-issues > .answer > .answer-detail')
                if mutation == 'delete': detail.select('p')[1].decompose()
                elif mutation == 'punctuation': detail.select('p')[1].string = 'AUTHORED-PURPOSE: N/A / 0 / Original.csv!'
                elif mutation == 'whole-keep': detail['style'] = 'break-inside: avoid'
                else: broken.select_one('#q-access-data').decompose()
                with self.assertRaises(AssertionError): compare(before, broken, pair[0], replies, language)

    def test_only_last_name_without_flags_releases_keep_and_names_stay_exact(self):
        from generate_pilot_fixtures import IDS, path
        produced = path('preservingCUuid', 'producedDataQUuid')
        selector = '#q-ethical-issues > .answer > ul > li:not(.ethical-project) > strong'
        for (language, escape, word), pair in self.pairs.items():
            for personal, sensitive in itertools.product([None, 'Yes', 'No'], repeat=2):
                replies = self.replies(language); item = replies[produced][-1]
                for field, choice in [('containPersonal', personal), ('containSensitive', sensitive)]:
                    if choice: replies[path(produced, item, field + 'QUuid')] = IDS[field + choice + 'AUuid']
                before, after, changes = check_case(pair, replies, language)
                names = after.select(selector)
                self.assertEqual([n.get_text() for n in before.select(selector)], [n.get_text() for n in names])
                self.assertTrue(all('style' not in n.attrs for n in names[:-1]))
                self.assertEqual(names[-1].get('style'), 'break-after: auto' if personal is sensitive is None else None)


if __name__ == '__main__': unittest.main()
