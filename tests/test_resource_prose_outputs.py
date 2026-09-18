import copy
import sys
from pathlib import Path
import unittest
from docx import Document
from lxml import etree as E
from test_resource_prose_trials import word

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from check_resource_prose_outputs import check_word,characters,W
from rehearse_resource_prose import join_word


def documents(language):
    source=word(language)
    # body() deliberately excludes cover provenance, starting with question 1.
    source.find(W+'body')[0].find(W+'r/'+W+'t').text='1. Original.csv: 0.'
    before=Document();before.element.replace(before.element.body,source.find(W+'body'))
    joined,_=join_word(before.element,language)
    after=Document();after.element.replace(after.element.body,joined.find(W+'body'))
    return before,after


class ResourceProseOutputTests(unittest.TestCase):
    def test_owned_word_join_allows_segmentation_but_not_content_changes(self):
        for language in ('english','chinese'):
            before,after=documents(language)
            self.assertTrue(check_word(before,after,language,True)['exact_body_outside_pair'])
            run=after.element.body[2].find(W+'r');value=run.find(W+'t').text
            run.find(W+'t').text=value[:2]
            following=E.Element(W+'r');E.SubElement(following,W+'t').text=value[2:];run.addnext(following)
            self.assertTrue(check_word(before,after,language,True)['character_formatting_preserved'])
            following.find(W+'t').text+='Extra.'
            with self.assertRaises(AssertionError):check_word(before,after,language,True)

    def test_formatting_unrelated_prose_and_false_selection_are_rejected(self):
        before,after=documents('english')
        with self.assertRaises(AssertionError):check_word(before,after,'english',False)
        altered=copy.deepcopy(after)
        p=altered.element.body[2];E.SubElement(E.SubElement(p.find(W+'r'),W+'rPr'),W+'b')
        with self.assertRaises(AssertionError):check_word(before,altered,'english',True)
        altered=copy.deepcopy(after);altered.element.body[-1].find(W+'r/'+W+'t').text='Rewritten.'
        with self.assertRaises(AssertionError):check_word(before,altered,'english',True)

    def test_run_fields_and_bookmarks_are_not_treated_as_text(self):
        _,after=documents('chinese');p=copy.deepcopy(after.element.body[2])
        E.SubElement(p.find(W+'r'),W+'fldChar')
        with self.assertRaises(AssertionError):characters(p)
        p=copy.deepcopy(after.element.body[2]);E.SubElement(p,W+'bookmarkStart')
        with self.assertRaises(AssertionError):characters(p)


if __name__=='__main__':unittest.main()
