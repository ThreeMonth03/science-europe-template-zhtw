"""Same-fixture Q3 delta across native HTML/PDF/editable Word and Word previews."""
import argparse
import copy
import difflib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from artifact_utils import sha
from check_budget_outputs import body, xml
from check_budget_spacing_outputs import pdf_raw_page_texts, line_box_overlaps
from check_identifier_concise_outputs import formatted_characters
from check_archive_gap_outputs import body_geometry
from check_narrative_outputs import compact
from check_short_budget_outputs import question_pages
from check_word_rhythm_outputs import assert_styles, inspect_preview
from check_word_short_budget_outputs import verify_preview_paragraphs
from check_format_reading_outputs import PLAIN_CJK, verified_format_markers

CASES = ['storage-missing', 'storage-partial', 'storage-zero', 'storage-complete', 'empty', 'negative']


def collapse(value): return ' '.join(value.split())


def capacity_texts(before, after):
    """The first owned paragraph changes; no authored subtree is matched."""
    old = before.select_one('.storage-conventions-policy')
    new = after.select_one('.storage-conventions-policy')
    if old is None:
        assert new is None; return None
    first = old.find('p', recursive=False)
    new_first = new.select_one('[data-fact-id="storage-capacity"]') or new.find('p', recursive=False)
    return (first.get_text() if first else '', new_first.get_text())


def check_changed_paragraph(old, new, before, after, expected, allow_body_style=False):
    p, q = Paragraph(old, before), Paragraph(new, after)
    assert q.text == expected, (q.text, expected)
    def props(n):
        value = n.find(qn('w:pPr'))
        return xml(value) if value is not None else None
    cloned = copy.deepcopy(new)
    if allow_body_style and p.style.name != q.style.name:
        assert p.style.name == 'First Paragraph' and q.style.name == 'Body Text'
        cloned.find(qn('w:pPr')).find(qn('w:pStyle')).set(qn('w:val'), p.style.style_id)
    assert props(old) == props(cloned), 'Unrelated paragraph properties changed'
    x, y = formatted_characters(old), formatted_characters(new)
    for op, i, j, k, l in difflib.SequenceMatcher(a=p.text, b=q.text, autojunk=False).get_opcodes():
        if op == 'equal': assert x[i:j] == y[k:l], 'Retained character formatting changed'
        else: assert all(style in {None, PLAIN_CJK} for _, style in x[i:j]+y[k:l]), 'Changed styled text'


def check_gap_paragraph(node, doc, text):
    assert node.tag == qn('w:p')
    p = Paragraph(node, doc); assert p.text == text and p.style.name == 'First Paragraph'
    props = node.find(qn('w:pPr'))
    assert props is not None and len(props) == 1 and props[0].tag == qn('w:pStyle')
    assert all(style in {None, PLAIN_CJK} for _, style in formatted_characters(node))


def word_delta(before, after, pairs, gap):
    left, right = body(before), body(after)
    active = False; i = j = changed = 0
    while i < len(left):
        a = left[i]; b = right[j]; p = Paragraph(a, before) if a.tag == qn('w:p') else None
        if p and p.style.name == 'Heading 3': active = p.text.startswith('3. ')
        if xml(a) == xml(b):
            i += 1; j += 1
            if active and gap and pairs and not pairs[0] and p and p.style.name == 'Heading 4':
                assert changed == 0
                check_gap_paragraph(right[j], after, collapse(pairs[1])); j += 1; changed += 1
            continue
        assert active and pairs and changed == 0, 'Unexpected Word change outside capacity'
        old, new = map(collapse, pairs)
        if gap:
            check_gap_paragraph(b, after, new); j += 1
            if old:
                assert p and p.text.startswith(old+' ')
                check_changed_paragraph(a, right[j], before, after, p.text[len(old)+1:], allow_body_style=True)
                i += 1; j += 1
        else:
            assert p and p.text.startswith(old)
            check_changed_paragraph(a, b, before, after, new+p.text[len(old):])
            i += 1; j += 1
        changed += 1
    assert j == len(right) and changed == int(pairs is not None)
    assert xml(before.part.numbering_part.element) == xml(after.part.numbering_part.element)
    links = lambda d: sorted(r.target_ref for r in d.part.rels.values() if r.is_external)
    assert links(before) == links(after)
    return changed


def pdf_delta(old, new, before, after, pairs):
    pages = [pdf_raw_page_texts(f) for f in [old, new]]
    boxes = [subprocess.check_output(['pdftotext', '-bbox-layout', str(f), '-']) for f in [old, new]]
    if pairs is None:
        assert question_pages(pages[0], before) == question_pages(pages[1], after)
        assert body_geometry(boxes[0], before) == body_geometry(boxes[1], after)
        return {'unchanged_control_geometry': True}
    cleaned = []; signatures = []
    h3 = compact(before.select_one('#q-docs-metadata h3').get_text())
    h4 = compact(before.select_one('#q-quality-control h3').get_text())
    for texts, bbox, soup in zip(pages, boxes, [before, after]):
        start = next(i for i, t in enumerate(texts) if h3 in t)
        clean, marks = verified_format_markers(texts, bbox, soup, start)
        cleaned.append(''.join(question_pages(clean, soup))); signatures.append(marks)
    assert signatures[0] == signatures[1], 'Generated list marker context/indent changed'
    prefix, rest = cleaned[0].split(h3, 1); middle, suffix = rest.split(h4, 1)
    old_text, new_text = map(compact, pairs)
    if old_text:
        assert middle.count(old_text) == 1
        middle = middle.replace(old_text, new_text, 1)
    else:
        heading = compact(before.select_one('#q-docs-metadata h4').get_text())
        assert middle.count(heading) == 1
        middle = middle.replace(heading, heading+new_text, 1)
    assert prefix+h3+middle+h4+suffix == cleaned[1], 'Unexpected PDF text/punctuation delta'
    return {'verified_generated_markers': sum(signatures[1].values())}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['build', 'prior', 'english']: p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--output', type=Path); a = p.parse_args()
    sys.path[:0] = [str(a.english.resolve()/n) for n in ['scripts', 'tests']]
    from storage_gap_contract import compare
    import check_missing_info_outputs as missing
    missing.HERE = a.english.resolve()
    report = {'selected_checks_passed': False, 'release_acceptance': False, 'rows': [],
        'checker_sha256': sha(Path(__file__)), 'contract_sha256': sha(a.english/'scripts/storage_gap_contract.py'),
        'helper_sha256': {n: sha(Path(__file__).with_name(n)) for n in ['check_budget_outputs.py', 'check_budget_spacing_outputs.py',
            'check_identifier_concise_outputs.py', 'check_archive_gap_outputs.py', 'check_narrative_outputs.py', 'check_short_budget_outputs.py',
            'check_word_rhythm_outputs.py', 'check_word_short_budget_outputs.py', 'check_format_reading_outputs.py', 'check_missing_info_outputs.py']},
        'package_sha256': {n: sha(a.build/n) for n in ['english.zip', 'chinese.zip']},
        'limits': ['Six synthetic cases per language; not all Q3 follow-ups or full DMP acceptance',
                   'PDF text normalizes whitespace, with exact HTML and editable Word checks separately',
                   'LibreOffice previews are not Microsoft Word acceptance; font-box overlaps are diagnostics, not ink collisions']}
    target = a.output or a.build/'storage-gap-report.json'; assert not target.exists()
    try:
        for case in CASES:
            for language in ['english', 'chinese']:
                stem = case+'-'+language; old = a.prior/'renders'/stem; new = a.build/'renders'/stem
                before = BeautifulSoup(old.with_suffix('.html').read_text(), 'html.parser')
                row, after = missing.inspect(a.build, case, language)
                locale = 'en' if language == 'english' else 'zh-Hant'
                events = json.loads((a.english/'fixtures/pilot'/locale/(case+'.events.json')).read_text())
                data = {e['path']: e['value']['value'] for e in events}
                compare(*[BeautifulSoup(str(s.select_one('#dmp-content')), 'html.parser') for s in [before, after]], data, language)
                pairs = capacity_texts(before, after)
                gap = bool(after.select('[data-fact-id="storage-capacity"][data-status="missing"]'))
                for fmt in ['html', 'pdf', 'docx']:
                    x, y = [json.loads(f.with_suffix('.'+fmt+'.fixture.json').read_text()) for f in [old, new]]
                    for key in ['recipe_sha256', 'events_sha256', 'km_sha256']: assert x[key] == y[key]
                    assert x['package_sha256'] == sha(a.prior/(language+'.zip'))
                    assert y['package_sha256'] == report['package_sha256'][language+'.zip']
                left, right = [Document(f.with_suffix('.docx')) for f in [old, new]]
                assert_styles(right); row['changed_word_capacity_blocks'] = word_delta(left, right, pairs, gap)
                with zipfile.ZipFile(old.with_suffix('.docx')) as x, zipfile.ZipFile(new.with_suffix('.docx')) as y:
                    for part in ['word/styles.xml', 'word/fontTable.xml']: assert x.read(part) == y.read(part)
                row['pdf_delta'] = pdf_delta(old.with_suffix('.pdf'), new.with_suffix('.pdf'), before, after, pairs)
                row['prior_pages'] = len(pdf_raw_page_texts(old.with_suffix('.pdf')))
                preview = a.build/'word-preview'/(stem+'.pdf'); old_preview = a.prior/'word-preview'/(stem+'.pdf')
                row['word_pages'] = inspect_preview(preview); row['prior_word_pages'] = inspect_preview(old_preview)
                row['preview_paragraphs_checked'] = verify_preview_paragraphs(right, preview, after)
                row['font_box_overlaps'] = {}
                for kind, files in [('pdf', [old.with_suffix('.pdf'), new.with_suffix('.pdf')]), ('word', [old_preview, preview])]:
                    boxes = [subprocess.check_output(['pdftotext', '-bbox-layout', str(f), '-']) for f in files]
                    row['font_box_overlaps'][kind] = dict(zip(['before', 'after'], map(line_box_overlaps, boxes)))
                    if pairs is None: assert body_geometry(boxes[0], before) == body_geometry(boxes[1], after)
                assert not row['errors'] and not row['reading_issues'], row
                row['capacity_change'] = pairs; row['capacity_missing'] = gap; row['passed'] = True
                artifacts = lambda root, f, prev: {str(path.relative_to(root)): sha(path) for path in
                    [f.with_suffix('.'+fmt+extra) for fmt in ['html', 'pdf', 'docx'] for extra in ['', '.fixture.json']]+[prev]}
                row['artifact_sha256'] = artifacts(a.build, new, preview)
                row['prior_artifact_sha256'] = artifacts(a.prior, old, old_preview)
                report['rows'].append(row)
                print(json.dumps({k: row[k] for k in ['case', 'language', 'pages', 'word_pages', 'capacity_missing']}), flush=True)
        report['selected_checks_passed'] = True
    except Exception as error: report['failure'] = repr(error); raise
    finally: target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__': main()
