import copy
from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from identifier_followup_contract import check_followups, ASSIGNERS
import test_identifier_followup_checks as historic
IDS = historic.IDS


class ConciseIdentifierChecks(unittest.TestCase):
    def fixture(self, language, known):
        _, soup, replies = historic.FollowupChecksTests().pair(language)
        parent = soup.select_one('[data-fact-id="persistent-identifier"]')
        parent.string = 'Persistent identifiers will be assigned.' if language == 'english' else '資料將取得持續識別碼。'
        if known:
            gap = soup.select_one('[data-fact-id="identifier-assigner"]')
            gap['data-status'] = 'complete'
            gap.string = ASSIGNERS['Repository'][0 if language == 'english' else 1]
            parent.clear(); parent.append(gap.extract())
            soup.select_one('.identifier-followups').decompose()
            base = next(k for k in replies if k.endswith(IDS['publishedDataIdentifierQUuid']))
            replies[base+'.'+IDS['publishedDataIdentifierYesAUuid']+'.'+IDS['publishedDataIdentifierAssignsQUuid']] = IDS['publishedDataIdentifierAssignsRepositoryAUuid']
        return soup, replies

    def test_both_facts_remain_and_missing_assigner_keeps_parent(self):
        for language in ['english', 'chinese']:
            for known in [False, True]:
                soup, replies = self.fixture(language, known)
                check_followups(soup, replies, IDS, language, concise=True)

    def test_missing_parent_wrong_state_and_extra_sentence_rejected(self):
        for mutation in ['parent-fact', 'state', 'text', 'extra', 'resolution']:
            soup, replies = self.fixture('chinese', True)
            parent = soup.select_one('[data-fact-id="persistent-identifier"]')
            if mutation == 'parent-fact': del parent['data-fact-id']
            elif mutation == 'state': parent['data-status'] = 'missing'
            elif mutation == 'text': parent.span.string = '不會指派識別碼。'
            elif mutation == 'extra': parent.append('資料將取得持續識別碼。')
            else: soup.select_one('[data-fact-id="identifier-resolution"]')['data-status'] = 'complete'
            with self.assertRaises(AssertionError):
                check_followups(soup, replies, IDS, 'chinese', concise=True)

    def test_same_named_distribution_does_not_share_actor(self):
        soup, replies = self.fixture('english', False)
        route = soup.select_one('.distribution-section')
        duplicate = copy.deepcopy(route); duplicate['data-item-id'] = 'unanswered-route'; route.insert_after(duplicate)
        key = next(k for k in replies if k.endswith(IDS['publishedDistrosQUuid']))
        replies[key].append('unanswered-route')
        with self.assertRaises(AssertionError):
            check_followups(soup, replies, IDS, 'english', concise=True)


if __name__ == '__main__': unittest.main()
