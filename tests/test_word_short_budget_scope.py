import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from probe_word_short_budget_scope import restore,remove_once,WORD_BRANCH,HELPER_BRANCH


class WordShortScopeTests(unittest.TestCase):
    def test_word_entry_only_removes_its_flag(self):
        self.assertEqual(restore('src/word/index.html.j2','prefix\n{%- set word_budget_reading = true -%}\noriginal'),'prefix\noriginal')

    def test_question_only_removes_exact_new_branch(self):
        self.assertEqual(restore('src/questions/15-required-resources.html.j2','prefix'+WORD_BRANCH+'suffix'),'prefixsuffix')
        with self.assertRaises(AssertionError):restore('src/questions/15-required-resources.html.j2',WORD_BRANCH.replace('true','false'))

    def test_lua_handler_and_insert_are_bounded(self):
        handler='  if div.identifier == "q-required-resources" then div = widen_short_budget_columns(div) end\n'
        source='original\n-- BEGIN short-budget Word columns\nnew function\n-- END short-budget Word columns\n\n'+handler+'tail'
        self.assertEqual(restore('src/word/pilot.lua',source),'original\ntail')
        self.assertEqual(restore('src/word/pilot.lua',source+'extra'),'original\ntailextra')

    def test_missing_duplicate_or_changed_anchor_rejected(self):
        for source in ['','marker marker']:
            with self.assertRaises(AssertionError):remove_once(source,'marker')
        source='macro short_table(original, rows, word=false) An output-specific hint\n'+HELPER_BRANCH
        expected='macro short_table(original, rows) A PDF-only hint\n    '+HELPER_BRANCH.splitlines()[3].lstrip()
        self.assertEqual(restore('src/budget-reading.html.j2',source),expected)


if __name__=='__main__':unittest.main()
