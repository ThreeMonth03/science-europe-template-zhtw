import copy
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from check_short_resource_rows_outputs import row_pages
from rehearse_profile_pdf import snapshot

BASE=ROOT/'reviews/2026-09-18-resource-prose-native/after'


class ShortResourceRowOutputTests(unittest.TestCase):
    def fixture(self):
        stem='budget-many-review-english'
        return snapshot(BASE/'native'/(stem+'.pdf'))[0],BeautifulSoup((BASE/'question-content'/(stem+'.html')).read_text(),'html.parser')

    def test_prior_native_row_seven_is_actually_split(self):
        pages,soup=self.fixture();rows=row_pages(pages,soup)
        self.assertEqual(len(rows),8);self.assertEqual(rows[6]['pages'],[8,9])
        self.assertTrue(all(r['paragraph_count']==5 for r in rows))

    def test_both_chinese_profiles_retain_their_real_prior_split(self):
        for profile,index in [('review',5),('submission',6)]:
            stem='budget-many-'+profile+'-chinese'
            pages=snapshot(BASE/'native'/(stem+'.pdf'))[0]
            soup=BeautifulSoup((BASE/'question-content'/(stem+'.html')).read_text(),'html.parser')
            rows=row_pages(pages,soup)
            with self.subTest(profile=profile):
                self.assertEqual(rows[index]['pages'],[7,8])
                self.assertEqual(sum(len(r['pages'])>1 for r in rows),1)

    def test_missing_duplicate_and_wrong_row_cells_are_rejected(self):
        pages,soup=self.fixture();compact=lambda s:''.join(s.split())
        source=soup.select_one('.resource-table tbody')
        rows=source.find_all('tr',recursive=False)
        amount=compact(rows[0].find_all('td',recursive=False)[1].get_text())
        other=compact(rows[1].find_all('td',recursive=False)[1].get_text())
        for replacement in ['',amount+amount,other]:
            bad=[p.replace(amount,replacement) for p in pages]
            with self.subTest(value=replacement),self.assertRaises(AssertionError):row_pages(bad,soup)

    def test_changed_paragraph_and_reordered_purpose_are_rejected(self):
        pages,soup=self.fixture();compact=lambda s:''.join(s.split())
        row=soup.select_one('.resource-table tbody tr')
        purpose=[compact(p.get_text()) for p in row.td.find_all('p')][1:]
        old=''.join(purpose)
        self.assertTrue(any(old in p for p in pages))
        for replacement in [old+'Changed.',''.join(reversed(purpose))]:
            bad=[p.replace(old,replacement,1) for p in pages]
            with self.assertRaises(AssertionError):row_pages(bad,soup)


if __name__=='__main__':unittest.main()
