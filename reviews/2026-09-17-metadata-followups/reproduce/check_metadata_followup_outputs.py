"""Same-fixture Q3 metadata proof: whole HTML, native PDF, editable Word and preview."""
import argparse
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

CASES = ['metadata-dictionary', 'metadata-dictionary-no', 'metadata-partial', 'metadata-private',
         'metadata-private-text', 'metadata-complete', 'empty', 'negative']


def collapse(value): return ' '.join(value.split())


def metadata_blocks(soup):
    """Bounded fixture oracle; Word joins adjacent fixed policy paragraphs only."""
    answer = soup.select_one('#q-docs-metadata .answer')
    policy = answer.select_one('.metadata-policy')
    if policy is None:
        values = answer.find_all(recursive=False)
        assert len(values) == 1 and values[0].name == 'p'
        return [('fixed', collapse(values[0].get_text()))]
    result, pending = [], []
    def flush():
        if pending: result.append(('fixed', ' '.join(pending))); pending.clear()
    for node in policy.find_all(recursive=False):
        if node.name == 'p': pending.append(collapse(node.get_text())); continue
        flush(); assert node.name == 'div'
        if 'reading-gap' in node.get('class', []):
            assert all(n.name == 'p' for n in node.find_all(recursive=False))
            result.extend(('fixed', collapse(n.get_text())) for n in node.find_all('p', recursive=False))
        else:
            assert node.get('class') == ['answer-detail'] and node.get('data-fact-id') == 'metadata-access-explanation'
            assert all(n.name in ['p', 'ul'] for n in node.find_all(recursive=False))
            result.extend(('authored', collapse(n.get_text())) for n in node.select('p, li'))
    flush(); return result


def word_parts(doc):
    nodes = body(doc)
    start = next(i for i, n in enumerate(nodes) if n.tag == qn('w:p') and
                 Paragraph(n, doc).style.name == 'Heading 3' and Paragraph(n, doc).text.startswith('3. '))+1
    end = next(i for i in range(start, len(nodes)) if nodes[i].tag == qn('w:p') and
               Paragraph(nodes[i], doc).style.name in ['Heading 3', 'Heading 4'])
    # Pandoc emits heading bookmarks as sibling nodes. They remain in the exact
    # unchanged suffix, not in the owned paragraph delta.
    while end > start and nodes[end-1].tag in [qn('w:bookmarkStart'), qn('w:bookmarkEnd')]: end -= 1
    return nodes[:start], nodes[start:end], nodes[end:]


def validate_word_region(nodes, doc, expected):
    assert len(nodes) == len(expected), (len(nodes), expected)
    authored = []
    for i, (node, (kind, text)) in enumerate(zip(nodes, expected)):
        assert node.tag == qn('w:p'); p = Paragraph(node, doc)
        assert p.text == text, (p.text, text)
        if kind == 'authored': authored.append(xml(node)); continue
        assert p.style.name == ('First Paragraph' if i == 0 else 'Body Text'), (i, p.style.name)
        props = node.find(qn('w:pPr'))
        assert props is not None and len(props) == 1 and props[0].tag == qn('w:pStyle')
        assert all(style in {None, PLAIN_CJK} for _, style in formatted_characters(node)), 'Unexpected fixed-text formatting'
        assert all(n.tag in {qn('w:pPr'), qn('w:r')} for n in node), 'Unexpected paragraph structure'
        assert all(child.tag in {qn('w:rPr'), qn('w:t')} for run in node.findall(qn('w:r')) for child in run), 'Unexpected non-text run'
    return authored


def word_delta(before, after, old_blocks, new_blocks):
    left, right = word_parts(before), word_parts(after)
    for i in [0, 2]: assert list(map(xml, left[i])) == list(map(xml, right[i])), 'Word changed outside metadata region'
    authored = [validate_word_region(nodes[1], doc, blocks) for nodes, doc, blocks in
                [(left, before, old_blocks), (right, after, new_blocks)]]
    assert authored[0] == authored[1], 'Authored Markdown formatting or paragraphs changed'
    assert xml(before.part.numbering_part.element) == xml(after.part.numbering_part.element)
    links = lambda d: sorted(r.target_ref for r in d.part.rels.values() if r.is_external)
    assert links(before) == links(after), 'Link destination changed'
    return {'before_blocks': len(old_blocks), 'after_blocks': len(new_blocks), 'authored_blocks': len(authored[1])}


def pdf_delta(old, new, before, after, changed):
    pages = [pdf_raw_page_texts(f) for f in [old, new]]
    boxes = [subprocess.check_output(['pdftotext', '-bbox-layout', str(f), '-']) for f in [old, new]]
    if not changed:
        assert question_pages(pages[0], before) == question_pages(pages[1], after)
        assert body_geometry(boxes[0], before) == body_geometry(boxes[1], after)
        return {'unchanged_control_geometry': True}
    h3 = compact(before.select_one('#q-docs-metadata h3').get_text())
    end = compact((before.select_one('#q-docs-metadata h4') or before.select_one('#q-quality-control h3')).get_text())
    signatures, outside = [], []
    for texts, bbox, soup in zip(pages, boxes, [before, after]):
        start = next(i for i, t in enumerate(texts) if h3 in t)
        clean, marks = verified_format_markers(texts, bbox, soup, start)
        text = ''.join(question_pages(clean, soup)); prefix, rest = text.split(h3, 1); middle, suffix = rest.split(end, 1)
        expected = ''.join(compact(value) for _, value in metadata_blocks(soup))
        assert middle == expected, ('PDF metadata text mismatch', middle, expected)
        signatures.append(marks); outside.append((prefix, suffix))
    assert signatures[0] == signatures[1], 'Generated marker text/indent changed'
    assert outside[0] == outside[1], 'Unexpected PDF text/punctuation change outside metadata'
    return {'verified_generated_markers': sum(signatures[1].values())}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['build', 'prior', 'english']: p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--output', type=Path); a = p.parse_args()
    sys.path[:0] = [str(a.english.resolve()/n) for n in ['scripts', 'tests']]
    from metadata_followup_contract import compare
    import check_missing_info_outputs as missing
    missing.HERE = a.english.resolve()
    helpers = ['check_budget_outputs.py', 'check_budget_spacing_outputs.py', 'check_identifier_concise_outputs.py',
        'check_archive_gap_outputs.py', 'check_narrative_outputs.py', 'check_short_budget_outputs.py',
        'check_word_rhythm_outputs.py', 'check_word_short_budget_outputs.py', 'check_format_reading_outputs.py',
        'check_missing_info_outputs.py', 'compare_runtime_outputs.py', 'check_format_outputs.py']
    report = {'selected_checks_passed': False, 'release_acceptance': False, 'rows': [],
        'checker_sha256': sha(Path(__file__)), 'contract_sha256': sha(a.english/'scripts/metadata_followup_contract.py'),
        'helper_sha256': {n: sha(Path(__file__).with_name(n)) for n in helpers},
        'package_sha256': {n: sha(a.build/n) for n in ['english.zip', 'chinese.zip']},
        'limits': ['Eight synthetic cases per language; not all Q3 states or full DMP acceptance',
                   'PDF normalizes whitespace; whole HTML and editable Word are checked separately',
                   'LibreOffice previews are not Microsoft Word acceptance; font-box overlaps are diagnostics, not ink collisions']}
    target = a.output or a.build/'metadata-followup-report.json'; assert not target.exists()
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
                changed = case not in ['empty', 'negative']
                for fmt in ['html', 'pdf', 'docx']:
                    x, y = [json.loads(f.with_suffix('.'+fmt+'.fixture.json').read_text()) for f in [old, new]]
                    for key in ['recipe_sha256', 'events_sha256', 'km_sha256']: assert x[key] == y[key]
                    assert x['package_sha256'] == sha(a.prior/(language+'.zip'))
                    assert y['package_sha256'] == report['package_sha256'][language+'.zip']
                left, right = [Document(f.with_suffix('.docx')) for f in [old, new]]
                assert_styles(right)
                if changed: row['word_metadata'] = word_delta(left, right, metadata_blocks(before), metadata_blocks(after))
                else: assert list(map(xml, body(left))) == list(map(xml, body(right))), 'Control Word body changed'
                with zipfile.ZipFile(old.with_suffix('.docx')) as x, zipfile.ZipFile(new.with_suffix('.docx')) as y:
                    for part in ['word/styles.xml', 'word/fontTable.xml']: assert x.read(part) == y.read(part)
                row['pdf_delta'] = pdf_delta(old.with_suffix('.pdf'), new.with_suffix('.pdf'), before, after, changed)
                row['prior_pages'] = len(pdf_raw_page_texts(old.with_suffix('.pdf')))
                preview = a.build/'word-preview'/(stem+'.pdf'); old_preview = a.prior/'word-preview'/(stem+'.pdf')
                row['word_pages'] = inspect_preview(preview); row['prior_word_pages'] = inspect_preview(old_preview)
                row['preview_paragraphs_checked'] = verify_preview_paragraphs(right, preview, after)
                row['font_box_overlaps'] = {}
                for kind, files in [('pdf', [old.with_suffix('.pdf'), new.with_suffix('.pdf')]), ('word', [old_preview, preview])]:
                    boxes = [subprocess.check_output(['pdftotext', '-bbox-layout', str(f), '-']) for f in files]
                    row['font_box_overlaps'][kind] = dict(zip(['before', 'after'], map(line_box_overlaps, boxes)))
                    if not changed: assert body_geometry(boxes[0], before) == body_geometry(boxes[1], after)
                assert not row['errors'] and not row['reading_issues'], row
                row['passed'] = True
                artifacts = lambda root, f, prev: {str(path.relative_to(root)): sha(path) for path in
                    [f.with_suffix('.'+fmt+extra) for fmt in ['html', 'pdf', 'docx'] for extra in ['', '.fixture.json']]+[prev]}
                row['artifact_sha256'] = artifacts(a.build, new, preview)
                row['prior_artifact_sha256'] = artifacts(a.prior, old, old_preview)
                report['rows'].append(row)
                print(json.dumps({k: row[k] for k in ['case', 'language', 'pages', 'prior_pages', 'word_pages', 'prior_word_pages']}), flush=True)
        report['selected_checks_passed'] = True
    except Exception as error: report['failure'] = repr(error); raise
    finally: target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__': main()
