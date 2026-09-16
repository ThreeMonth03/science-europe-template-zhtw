"""Pagination-only trials on frozen DOCX; these are NOT native template exports."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

from bs4 import BeautifulSoup
from docx import Document
from lxml import etree as E

from artifact_utils import sha
from check_word_rhythm_outputs import assert_styles, inspect_preview
from check_word_short_budget_outputs import verify_preview_paragraphs, word_pages

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}
PROFILES = ['baseline', 'release-budget-heading', 'release-table-labels', 'keep-overview']
CASES = ['partial', 'budget-mixed-gaps', 'personal-transfer-complete']


def q(name):
    return '{' + W + '}' + name


def text(node):
    return ''.join(node.itertext())


def compact(value):
    return ''.join(value.split())


def select(root):
    """Reject ambiguous targets instead of guessing another table or section."""
    body = root.find(q('body'))
    tables = body.findall(q('tbl'))
    table = tables[-1]
    starts = [n for n in body if n.tag == q('p') and text(n).startswith('15. ')]
    assert len(starts) == 1
    leading = [n for n in list(body)[body.index(starts[0]):body.index(table)] if n.tag == q('p')]
    assert len(leading) >= 2
    heading = leading[-1]
    assert heading.find('w:pPr/w:pStyle', NS).get(q('val')) == 'Heading4'
    assert compact(text(heading)) in ['Data-managementbudget', '資料管理預算']
    header = compact(text(table.find(q('tr'))))
    assert 'Resourceandpurpose' in header or '資源項目與用途' in header
    return table, leading


def transform(root, profile):
    assert profile in PROFILES
    result = copy.deepcopy(root)
    table, leading = select(result)
    targets = []
    value = '0'
    if profile == 'release-budget-heading':
        targets = [leading[-1]]
    elif profile == 'release-table-labels':
        targets = [p for p in table.iter(q('p'))
                   if p.find('w:pPr/w:pStyle', NS) is not None
                   and p.find('w:pPr/w:pStyle', NS).get(q('val')) == 'PilotLabel']
        assert targets
    elif profile == 'keep-overview':
        targets, value = leading, '1'
    for p in targets:
        properties = p.find(q('pPr'))
        if properties is None:
            properties = E.Element(q('pPr'))
            p.insert(0, properties)
        assert properties.find(q('keepNext')) is None
        # keepNext precedes the other pagination/spacing properties in OOXML.
        position = 1 if properties.find(q('pStyle')) is not None else 0
        properties.insert(position, E.Element(q('keepNext'), {q('val'): value}))
    validate_change(root, result, profile)
    return result, len(targets)


def validate_change(before, after, profile):
    """Restore ONLY designated direct keepNext additions, then compare all XML."""
    restored = copy.deepcopy(after)
    table, leading = select(restored)
    original_table, original_leading = select(before)
    if profile == 'release-budget-heading':
        targets, originals, value = [leading[-1]], [original_leading[-1]], '0'
    elif profile == 'release-table-labels':
        def labels(t):
            return [p for p in t.iter(q('p')) if p.find('w:pPr/w:pStyle', NS) is not None
                    and p.find('w:pPr/w:pStyle', NS).get(q('val')) == 'PilotLabel']
        targets, originals, value = labels(table), labels(original_table), '0'
    elif profile == 'keep-overview':
        targets, originals, value = leading, original_leading, '1'
    else:
        assert profile == 'baseline'
        targets, originals, value = [], [], None
    assert len(targets) == len(originals)
    for p, old in zip(targets, originals):
        props = p.find(q('pPr'))
        keeps = props.findall(q('keepNext'))
        assert len(keeps) == 1 and keeps[0].attrib == {q('val'): value}
        props.remove(keeps[0])
        if old.find(q('pPr')) is None:
            assert not len(props) and not props.attrib
            p.remove(props)
    assert E.tostring(before, method='c14n') == E.tostring(restored, method='c14n'), 'Non-pagination XML changed'


def locations(root, pdf):
    table, leading = select(root)
    raw = subprocess.check_output(['pdftotext', '-raw', str(pdf), '-'], text=True)
    bbox = subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-'])
    pages = word_pages(raw, bbox)
    anchors = {'question': text(leading[0]), 'overview_first': text(leading[1]),
               'overview_last': text(leading[-2]), 'budget_heading': text(leading[-1])}
    for index, row in enumerate(table.findall(q('tr'))[1:], 1):
        anchors['resource_' + str(index)] = text(row.find('w:tc/w:p', NS))
    return {key: [i for i, page in enumerate(pages, 1) if compact(value) in page]
            for key, value in anchors.items()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prior', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cases', nargs='+', choices=CASES, default=CASES)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    report = {'completed': False, 'release_acceptance': False, 'native_export': False,
              'checker_sha256': sha(Path(__file__)), 'rows': [],
              'limits': ['Copied frozen DOCX, not a template implementation',
                         'LibreOffice only, not Microsoft Word',
                         'Disabling label/heading keeps is diagnostic, not an accepted layout rule']}
    target = a.output / 'report.json'

    def save():
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    save()
    try:
        for case in a.cases:
            for language in ['english', 'chinese']:
                stem = case + '-' + language
                source = a.prior / 'renders' / (stem + '.docx')
                html = source.with_suffix('.html')
                soup = BeautifulSoup(html.read_text(), 'html.parser')
                with zipfile.ZipFile(source) as archive:
                    entries = {n: archive.read(n) for n in archive.namelist()}
                original = E.fromstring(entries['word/document.xml'])
                for profile in PROFILES:
                    root, edits = transform(original, profile)
                    out = a.output / (stem + '-' + profile + '.docx')
                    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
                        for name, data in entries.items():
                            archive.writestr(name, E.tostring(root) if name == 'word/document.xml' and edits else data)
                    with zipfile.ZipFile(out) as archive:
                        assert set(archive.namelist()) == set(entries)
                        assert all(archive.read(n) == data for n, data in entries.items() if n != 'word/document.xml')
                    with tempfile.TemporaryDirectory(prefix='se-budget-tail-lo-') as temp:
                        subprocess.run(['libreoffice', '-env:UserInstallation=' + Path(temp).as_uri(),
                                        '--headless', '--convert-to', 'pdf', '--outdir', str(a.output), str(out)],
                                       check=True, capture_output=True, timeout=120)
                    pdf = out.with_suffix('.pdf')
                    document = Document(out)
                    assert_styles(document)
                    row = {'case': case, 'language': language, 'profile': profile,
                           'pages': inspect_preview(pdf), 'anchors': locations(root, pdf),
                           'added_direct_keepNext_properties': edits,
                           'paragraphs_checked': verify_preview_paragraphs(document, pdf, soup),
                           'only_designated_keepNext_changed': True, 'all_other_package_parts_identical': True,
                           'source_sha256': sha(source), 'source_html_sha256': sha(html),
                           'docx_sha256': sha(out), 'preview_sha256': sha(pdf)}
                    report['rows'].append(row)
                    save()
                    print(json.dumps(row, ensure_ascii=False), flush=True)
        report['completed'] = True
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
