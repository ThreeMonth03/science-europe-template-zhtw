import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_q8_word_scope import verify_translations


class Q8ScopeTests(unittest.TestCase):
    def test_empty_identifier_list_matches_manifest_contract(self):
        value={'translation_tree_sha256':{str(i):str(i) for i in range(731)},'untranslated_units':[]}
        verify_translations(value,copy.deepcopy(value))

    def test_untranslated_identifier_or_translation_edit_is_rejected(self):
        old={'translation_tree_sha256':{str(i):str(i) for i in range(731)},'untranslated_units':[]}
        for field,value in [('untranslated_units',['missing-unit']),('untranslated_units',0),
                            ('translation_tree_sha256',{**old['translation_tree_sha256'],'1':'changed'})]:
            new=copy.deepcopy(old);new[field]=value
            with self.assertRaises(AssertionError):verify_translations(old,new)
