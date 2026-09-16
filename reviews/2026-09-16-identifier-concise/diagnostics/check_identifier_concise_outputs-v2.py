"""Same-fixture native Q13 prose delta, retaining every other answer and Word style."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from lxml import etree
from artifact_utils import sha
from check_budget_outputs import body, xml
from check_budget_spacing_outputs import pdf_raw_page_texts
from check_identifier_followup_outputs import check_followup_page_text
from check_narrative_outputs import compact
from check_pdf_budget_reading_outputs import question_pages
from check_word_rhythm_outputs import assert_styles, inspect_preview
from check_word_short_budget_outputs import verify_preview_paragraphs
from compare_runtime_outputs import markers
from identifier_followup_contract import check_followups

CASES = ['budget-mixed-gaps','identifier-followups','partial','empty','negative',
         'personal-transfer-complete','budget-long-no-currency','budget-many']


def verified_list_suffixes(pages, bbox, soup):
    """WeasyPrint paints generated markers last; verify their visual list lines first."""
    assert '•' not in soup.get_text(), 'Authored bullet characters need a different oracle'
    geometry = etree.fromstring(bbox).findall('.//{*}page')
    assert len(geometry) == len(pages)
    signatures = Counter(); clean = []
    for page, node in zip(pages, geometry):
        text = page.rstrip('•')
        assert '•' not in text, 'Only a verified generated page suffix may be removed'
        bullets = [w for w in node.findall('.//{*}word') if w.text == '•']
        assert len(page)-len(text) == len(bullets)
        for word in bullets:
            line = word.getparent()
            assert etree.QName(line).localname == 'line'
            value = compact(''.join(line.itertext()))
            assert value.startswith('•') and len(value) > 1 and value.count('•') == 1
            signatures[(value,round(float(word.get('xMin')),3))] += 1
        clean.append(text)
    return clean, signatures


def policy_pairs(before, after):
    result = []
    old = before.select('#q-persistent-identifier .identifier-arrangement')
    new = after.select('#q-persistent-identifier .identifier-arrangement')
    assert len(old) == len(new)
    for left, right in zip(old, new):
        if left.select('[data-fact-id="identifier-assigner"]'):
            sentences = lambda n: ' '.join(p.get_text() for p in n.find_all('p', recursive=False))
            result.append((sentences(left), sentences(right)))
    return result


def formatted_characters(node):
    """Allow harmless run regrouping, but preserve formatting of each retained character."""
    result = []
    for child in node:
        if child.tag == qn('w:pPr'): continue
        assert child.tag == qn('w:r'), 'Unexpected non-owned paragraph structure'
        props = child.find(qn('w:rPr'))
        style = xml(props) if props is not None else None
        for part in child:
            assert part.tag in [qn('w:rPr'), qn('w:t')]
            if part.tag == qn('w:t'):
                result.extend((character, style) for character in part.text or '')
    return result


def compare_word(before, after, pairs):
    old, new = body(before), body(after)
    assert len(old) == len(new)
    active = False; count = 0
    for left, right in zip(old, new):
        assert left.tag == right.tag
        if left.tag == qn('w:p'):
            p, q = Paragraph(left, before), Paragraph(right, after)
            if p.style.name == 'Heading 3' and p.text.startswith('13. '): active = True
            if p.style.name == 'Heading 3' and p.text.startswith('14. '): active = False
        if xml(left) == xml(right): continue
        assert active and left.tag == qn('w:p') and count < len(pairs), 'Unapproved Word block change'
        expected_before, expected_after = pairs[count]
        assert p.text == expected_before and q.text == expected_after, 'Wrong policy change or wrong distribution order'
        assert expected_before.endswith(expected_after)
        removed = len(expected_before) - len(expected_after)
        assert removed > 0
        assert xml(left.find(qn('w:pPr'))) == xml(right.find(qn('w:pPr'))), 'Policy style changed'
        assert formatted_characters(left)[removed:] == formatted_characters(right), 'Retained formatting changed'
        count += 1
    assert count == len(pairs)
    return count


def pdf_delta(old_pages, new_pages, before, after, pairs):
    left = ''.join(question_pages(old_pages, before)); right = ''.join(question_pages(new_pages, after))
    h13 = compact(before.select_one('#q-persistent-identifier h3').get_text())
    h14 = compact(before.select_one('#q-dm-responsible h3').get_text())
    assert left.count(h13) == left.count(h14) == right.count(h13) == right.count(h14) == 1
    prefix, tail = left.split(h13, 1); middle, suffix = tail.split(h14, 1)
    cursor = 0
    for old, new in pairs:
        old, new = compact(old), compact(new)
        index = middle.find(old, cursor); assert index >= 0
        middle = middle[:index] + new + middle[index+len(old):]
        cursor = index+len(new)
    assert prefix+h13+middle+h14+suffix == right, 'Unexpected native PDF body text change'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['build','prior','prior-followups','english']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--cases', nargs='+', default=CASES)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    sys.path.insert(0, str(a.english.resolve()/'scripts'))
    from identifier_concise_contract import compare
    from generate_pilot_fixtures import IDS
    import check_missing_info_outputs as missing
    missing.HERE = a.english.resolve()
    report = {'selected_checks_passed': False, 'release_acceptance': False, 'rows': [],
              'checker_sha256': sha(Path(__file__)),
              'package_sha256': {n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
              'limits': ['Eight synthetic cases per language, not every questionnaire',
                         'LibreOffice is not Microsoft Word acceptance',
                         'Only Q13 repeated affirmative prose may disappear; facts and original translations remain']}
    target = a.output or a.build/'identifier-concise-report.json'; assert not target.exists()
    try:
        for case in a.cases:
            prior = a.prior_followups if case == 'identifier-followups' else a.prior
            for language in ['english','chinese']:
                stem = case+'-'+language
                old, new = [root/'renders'/stem for root in [prior,a.build]]
                before = BeautifulSoup(old.with_suffix('.html').read_text(),'html.parser')
                row, after = missing.inspect(a.build,case,language)
                assert markers(before) == markers(after)
                for q in before.select('.question'):
                    current = after.find(id=q['id'])
                    if q['id'] != 'q-persistent-identifier': assert str(q) == str(current)
                    else: row['shortened_assignment_units'] = compare(BeautifulSoup(str(q),'html.parser'),BeautifulSoup(str(current),'html.parser'),language)
                locale = 'en' if language == 'english' else 'zh-Hant'
                events = json.loads((a.english/'fixtures/pilot'/locale/(case+'.events.json')).read_text())
                replies = {e['path']: e['value']['value'] for e in events}
                check_followups(after,replies,IDS,language,concise=True)
                for fmt in ['html','pdf','docx']:
                    x,y = [json.loads(n.with_suffix('.'+fmt+'.fixture.json').read_text()) for n in [old,new]]
                    for key in ['recipe_sha256','events_sha256','km_sha256']: assert x[key] == y[key]
                    assert x['package_sha256'] == sha(prior/(language+'.zip'))
                    assert y['package_sha256'] == report['package_sha256'][language+'.zip']
                pairs = policy_pairs(before,after)
                assert len(pairs) == row['shortened_assignment_units']
                left,right = [Document(n.with_suffix('.docx')) for n in [old,new]]
                assert_styles(right); row['word_policy_changes'] = compare_word(left,right,pairs)
                links = lambda d: sorted(r.target_ref for r in d.part.rels.values() if r.is_external)
                assert links(left) == links(right)
                with zipfile.ZipFile(old.with_suffix('.docx')) as x, zipfile.ZipFile(new.with_suffix('.docx')) as y:
                    for part in ['word/styles.xml','word/fontTable.xml','word/numbering.xml']:
                        assert x.read(part) == y.read(part)
                old_pages,new_pages = [pdf_raw_page_texts(n.with_suffix('.pdf')) for n in [old,new]]
                clean_old, old_bullets = verified_list_suffixes(old_pages,subprocess.check_output(['pdftotext','-bbox-layout',str(old.with_suffix('.pdf')),'-']),before)
                clean_new, new_bullets = verified_list_suffixes(new_pages,subprocess.check_output(['pdftotext','-bbox-layout',str(new.with_suffix('.pdf')),'-']),after)
                assert old_bullets == new_bullets, 'Generated list markers changed list text, count or indentation'
                row['visually_bound_bullets_checked'] = sum(new_bullets.values())
                pdf_delta(clean_old,clean_new,before,after,pairs)
                row['prior_pages'] = len(old_pages)
                assert row['pages'] <= row['prior_pages'], 'Native PDF page count increased'
                preview = a.build/'word-preview'/(stem+'.pdf')
                row['word_pages'] = inspect_preview(preview)
                row['prior_word_pages'] = inspect_preview(prior/'word-preview'/(stem+'.pdf'))
                assert row['word_pages'] <= row['prior_word_pages'], 'Word preview page count increased'
                row['preview_paragraphs_checked'] = verify_preview_paragraphs(right,preview,after)
                for kind,path in [('pdf',new.with_suffix('.pdf')),('word',preview)]:
                    row[kind+'_q13_units'] = check_followup_page_text(subprocess.check_output(['pdftotext','-layout',str(path),'-'],text=True),after)
                for path in [new.with_suffix('.docx'),new.with_suffix('.docx.fixture.json'),preview]:
                    row['artifact_sha256'][str(path.relative_to(a.build))] = sha(path)
                row['prior_root'] = str(prior)
                row['prior_artifact_sha256'] = {str(f.relative_to(prior)):sha(f)
                    for f in [old.with_suffix('.'+fmt+extra) for fmt in ['html','pdf','docx'] for extra in ['','.fixture.json']]
                    +[prior/'word-preview'/(stem+'.pdf')]}
                report['rows'].append(row)
                print(json.dumps({k:row[k] for k in ['case','language','pages','word_pages','shortened_assignment_units','errors','reading_issues']}),flush=True)
        report['selected_checks_passed'] = len(report['rows']) == 2*len(a.cases) and all(not r['errors'] and not r['reading_issues'] for r in report['rows'])
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    assert report['selected_checks_passed']


if __name__ == '__main__': main()
