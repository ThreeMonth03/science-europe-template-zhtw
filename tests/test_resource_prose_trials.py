import copy
from pathlib import Path
import sys
import unittest
from lxml import etree as E

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from rehearse_resource_prose import Q15,HARDWARE,SENTENCES,join_html,join_word,word_prefix_geometry,W,c14n,text


def html(language='chinese',ending=1):
    first,endings=SENTENCES[language]
    return '<article><p>Original.csv: 0.</p>'+Q15+'<h3>15. Resources?</h3><div class="answer">'+HARDWARE+first+'</p>\n<p>'+endings[ending]+'</p><div class="answer-detail"><p>保留。  Original.csv！</p></div></div></div></article>'


def word(language='chinese'):
    root=E.Element(W+'document',nsmap={'w':W[1:-1]});body=E.SubElement(root,W+'body')
    for value,style in [('Original.csv: 0.','BodyText'),('15. Resources?','Heading3'),(SENTENCES[language][0],'PilotLead'),(SENTENCES[language][1][1],'PilotLead'),('保留。  Original.csv！','BodyText')]:
        p=E.SubElement(body,W+'p');E.SubElement(E.SubElement(p,W+'pPr'),W+'pStyle',{W+'val':style})
        E.SubElement(E.SubElement(p,W+'r'),W+'t').text=value
    return root


class ResourceProseTrials(unittest.TestCase):
    def test_word_prefix_only_allows_missing_cover_footer(self):
        source=b'<html><page height="1000"><line yMin="20"><word>Cover.</word></line></page><page height="1000"><line yMin="20"><word>15.</word></line><line yMin="950"><word>2/2</word></line></page></html>'
        self.assertEqual(word_prefix_geometry(source),[(1,{},'Cover.')])
        for wrong in (source.replace(b'2/2',b'Other'),source.replace(b'950',b'500'),source.replace(b'Cover.',b'15.')):
            with self.assertRaises(AssertionError):word_prefix_geometry(wrong)

    def test_only_exact_fixed_pair_joins_in_both_languages(self):
        for language in SENTENCES:
            for ending in (0,1):
                source=html(language,ending);after,selected=join_html(source,language)
                self.assertTrue(selected)
                first,endings=SENTENCES[language]
                expected=source.replace(first+'</p>\n<p>'+endings[ending],first+(' ' if language=='english' else '')+'<span data-fact-id="repository-charges" data-status="complete">'+endings[ending]+'</span>')
                self.assertEqual(after,expected)

    def test_html_missing_unknown_authored_and_ambiguous_cases_stay_identical(self):
        original=html();first,endings=SENTENCES['chinese']
        cases=[original.replace('explicit-no','missing'),original.replace('explicit-no','unknown'),
               original.replace('data-fact-id="hardware-software"','data-fact-id="another"'),
               original.replace(first,first+'自填。'),original.replace(endings[1],'尚待補充：是否收費。'),
               original.replace('<p>'+endings[1],'<p class="data-gap">'+endings[1]),
               original.replace(first,'<strong>'+first+'</strong>'),
               original.replace('</p>\n<p>','</p><div>別的回答。</div><p>'),
               original.replace('</p>\n<p>','</p><!-- do not cross --><p>'),
               original.replace(HARDWARE,'<div class="answer-detail">'+HARDWARE).replace('</article>','</div></article>'),
               original+original,original.replace('id="q-required-resources"','id="q-other"')]
        for i,source in enumerate(cases):
            with self.subTest(case=i):self.assertEqual(join_html(source,'chinese'),(source,False))

    def test_word_retains_exact_runs_and_does_not_mutate_input(self):
        for language in SENTENCES:
            source=word(language);saved=c14n(source);after,selected=join_word(source,language)
            self.assertTrue(selected);self.assertEqual(c14n(source),saved)
            values=[text(p) for p in after.find(W+'body')]
            self.assertEqual(values,[ 'Original.csv: 0.','15. Resources?', SENTENCES[language][0]+(' ' if language=='english' else '')+SENTENCES[language][1][1], '保留。  Original.csv！'])
            self.assertEqual(join_word(after,language)[1],False)

    def test_word_rejects_different_styles_bookmarks_fields_and_extra_text(self):
        cases=[]
        root=word();root.find(W+'body')[3].find(W+'pPr/'+W+'pStyle').set(W+'val','BodyText');cases.append(root)
        root=word();E.SubElement(root.find(W+'body')[3],W+'bookmarkStart',{W+'id':'3',W+'name':'keep'});cases.append(root)
        root=word();E.SubElement(root.find(W+'body')[3].find(W+'r'),W+'fldChar',{W+'fldCharType':'begin'});cases.append(root)
        root=word();root.find(W+'body')[3].find(W+'r/'+W+'t').text+='Original.csv';cases.append(root)
        root=word();root.find(W+'body')[1].find(W+'r/'+W+'t').text='14. Other';cases.append(root)
        root=word();root.find(W+'body').append(copy.deepcopy(root.find(W+'body')[1]));cases.append(root)
        for i,source in enumerate(cases):
            with self.subTest(case=i):
                result,selected=join_word(source,'chinese');self.assertFalse(selected);self.assertEqual(c14n(result),c14n(source))


if __name__=='__main__':unittest.main()
