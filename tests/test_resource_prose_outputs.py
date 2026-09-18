import copy
import sys
from pathlib import Path
import unittest
from docx import Document
from lxml import etree as E
from bs4 import BeautifulSoup
from test_resource_prose_trials import word

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from check_resource_prose_outputs import check_word,characters,continuation_headers,canonical_many_rows,W
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
    def test_many_rows_accepts_paint_order_not_lost_or_wrong_row_content(self):
        rows=''.join(f'<tr><td><p>R{i}:</p><p>A{i}.</p><p>B{i}.</p></td><td><p>{i}TWD</p></td><td><p>F{i}.</p></td></tr>' for i in range(1,9))
        soup=BeautifulSoup('<div id="q-required-resources"><table class="resource-table"><tbody>'+rows+'</tbody></table></div>','html.parser')
        original='Prefix'+''.join(f'R{i}:A{i}.B{i}.{i}TWDF{i}.' for i in range(1,9))
        reordered='Prefix'+''.join(f'R{i}:{i}TWDF{i}.A{i}.B{i}.' for i in range(1,9))
        self.assertEqual(canonical_many_rows(['Cover',reordered],soup),[original])
        for value in [reordered.replace('F3.',''),reordered.replace('3TWD','4TWD'),
                      reordered.replace('A3.','A3.A3.'),reordered.replace('A3.B3.','B3.A3.'),
                      reordered.replace('R3:','R2:')]:
            with self.assertRaises(AssertionError):canonical_many_rows(['Cover',value],soup)

    def test_only_exact_continuation_identity_at_page_start_is_removed(self):
        soup=BeautifulSoup('<div id="q-required-resources"><h3>15. Resources?</h3><table class="resource-table"><thead><tr><th>Header</th></tr></thead><tbody><tr><td><p>Name</p><div class="answer-detail"><p>Authored.</p></div></td><td>0</td><td>Funds</td></tr></tbody></table></div>','html.parser')
        identity='HeaderName0Funds';pages=['Cover','15.Resources?',identity+'First.',identity+'Second.','Keep'+identity+'inline.']
        projected,removed=continuation_headers(pages,soup,'budget-long-no-currency')
        self.assertEqual(removed,[4]);self.assertEqual(projected,[*pages[:3],'Second.',pages[4]])
        self.assertEqual(continuation_headers(pages,soup,'empty'),(pages,[]))
        with self.assertRaises(AssertionError):continuation_headers(pages[:3],soup,'budget-long-no-currency')
        soup.select_one('.answer-detail p').string=identity
        with self.assertRaises(AssertionError):continuation_headers(pages,soup,'budget-long-no-currency')

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

    def test_first_body_alias_requires_identical_reference_settings(self):
        before,after=documents('english')
        for document in (before,after):
            if 'First Paragraph' not in document.styles:
                document.styles.add_style('First Paragraph',1).base_style=document.styles['Body Text']
            first_style=document.styles['First Paragraph'].element
            body_style=document.styles['Body Text'].element
            for style in (first_style,body_style):
                for name in ('pPr','rPr'):
                    for old in list(style.findall(W+name)):style.remove(old)
                    E.SubElement(style,W+name)
            first_style.find(W+'basedOn').set(W+'val','BodyText')
            document.element.body[2].find(W+'pPr/'+W+'pStyle').set(W+'val','FirstParagraph')
        before.element.body[3].find(W+'pPr/'+W+'pStyle').set(W+'val','BodyText')
        self.assertTrue(check_word(before,after,'english',True)['joined'])
        E.SubElement(before.styles['First Paragraph'].element.find(W+'rPr'),W+'b')
        with self.assertRaises(AssertionError):check_word(before,after,'english',True)


if __name__=='__main__':unittest.main()
