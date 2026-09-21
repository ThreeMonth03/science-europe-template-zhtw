"""Compare the local native prototype, not a release or whole-template acceptance."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from lxml import etree as E
from artifact_utils import sha
from rehearse_mixed_budget import content, MARKERS, compact
from rehearse_profile_pdf import snapshot, prefix_geometry
from rehearse_profile_pagination import geometry
from check_short_resources_outputs import fonts
from check_budget_outputs import body, xml
from check_word_short_budget_outputs import verify_preview_paragraphs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
from compact import compact_source
from prototype import TAIL


def page_bounds(bbox):
    """Check actual PDF word boxes, never infer clipping from a UI thumbnail."""
    result = []
    pages = E.fromstring(bbox).findall('.//{*}page')
    for index, page in enumerate(pages, 1):
        footer = set()
        for line in page.findall('.//{*}line'):
            words = line.findall('{*}word')
            if ''.join(w.text or '' for w in words) == f'{index}/{len(pages)}' and float(line.get('yMin')) > float(page.get('height')) * .9:
                footer.update(words)
        assert footer
        for word in page.findall('.//{*}word'):
            if word in footer:
                continue
            if (float(word.get('xMin')) < 0 or float(word.get('xMax')) > float(page.get('width')) or
                    float(word.get('yMin')) < 0 or float(word.get('yMax')) > float(page.get('height')) - 22 * 72 / 25.4 + 3):
                result.append({'page': index, 'text': word.text, 'box': dict(word.attrib)})
    return result


def long_tail_together(pages, source):
    soup = BeautifulSoup(source, 'html.parser')
    table = soup.select_one('.pdf-resource-reading')
    allocation = compact(table.tbody.td.find_all('p', recursive=False)[-1].get_text())
    para = 'MIX-LONG-09-PARA-60:'
    marker_pages = [i for i, page in enumerate(pages, 1) if para in page]
    allocation_pages = [i for i, page in enumerate(pages, 1) if allocation in page]
    # Short rows can contain the same allocation. Scope the final occurrence to
    # the unique long-purpose marker and the end of this synthetic document.
    assert len(marker_pages) == 1 and allocation_pages
    return marker_pages[0] == allocation_pages[-1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'captures', 'english', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    a.output.mkdir(parents=True)
    sys.path.insert(0, str(a.english.resolve() / 'scripts'))
    from short_resource_rows_contract import project_hints
    captures = {sha(path): path.name.split('.')[0] for path in a.captures.glob('*.output.pdf')}
    report = {'native_export': True, 'prototype_only': True, 'release_acceptance': False,
              'microsoft_word_acceptance': False, 'full_control_matrix_complete': False,
              'checker_sha256': sha(Path(__file__)), 'rows': []}
    for case in ['mixed-long-last', 'mixed-gaps']:
        for profile in ['review', 'submission']:
            for language in ['english', 'chinese']:
                stem = '-'.join([case, profile, language])
                paths = [folder / 'renders' / (stem + '.pdf') for folder in [a.before, a.after]]
                inputs = []
                for phase, path in zip(['before', 'after'], paths):
                    capture = captures[sha(path)]
                    raw = a.captures / (capture + '.input.html')
                    compacted, assets = compact_source(raw.read_bytes())
                    target = a.output / (stem + '-' + phase + '.input.html')
                    target.write_bytes(compacted)
                    inputs.append(compacted.decode())
                    proof = {'full_input_sha256': sha(raw), 'compact_input_sha256': sha(target),
                             'fonts': assets, 'capture_prefix': capture, 'pdf_sha256': sha(path)}
                    target.with_suffix('.json').write_text(json.dumps(proof, indent=2) + '\n')
                assert inputs[1].count(TAIL) == 1
                projected = inputs[1].replace(TAIL, '', 1)
                assert projected.count('<tbody style="break-inside: avoid">') == 1
                projected = projected.replace('<tbody style="break-inside: avoid">', '<tbody>', 1)
                assert project_hints(projected) == inputs[0], 'Unowned PDF-entry input delta'
                snapshots = [snapshot(path) for path in paths]
                parsed = [content(v[0], inputs[0]) for v in snapshots]
                assert parsed[0]['canonical'] == parsed[1]['canonical']
                assert Counter(c for c in ''.join(snapshots[0][0]) if c in MARKERS) == Counter(c for c in ''.join(snapshots[1][0]) if c in MARKERS)
                assert prefix_geometry(snapshots[0][1]) == prefix_geometry(snapshots[1][1])
                assert fonts(paths[0]) == fonts(paths[1])
                assert all(len(row['pages']) == 1 for row in parsed[1]['rows'])
                missing = []
                for value in parsed:
                    repeated = {r['page'] for r in value['repeated_headers'] if r['kind'] == 'long-identity'}
                    missing.append(sorted(set(value['long_pages'][1:]) - repeated))
                assert not missing[1], 'Candidate continuation header missing'
                bounds = [page_bounds(v[1]) for v in snapshots]
                assert bounds[1] == bounds[0], 'New clipping or bottom-margin intrusion'
                assert long_tail_together(snapshots[1][0], inputs[1]), 'Isolated long allocation'
                html = [compact_source((folder / 'renders' / (stem + '.html')).read_bytes())[0].decode() for folder in [a.before, a.after]]
                assert html[1].replace(TAIL, '', 1) == html[0]
                docs = [Document(folder / 'renders' / (stem + '.docx')) for folder in [a.before, a.after]]
                assert [xml(n) for n in body(docs[0])] == [xml(n) for n in body(docs[1])]
                assert [sorted(r.target_ref for r in doc.part.rels.values() if r.is_external) for doc in docs][0] == [sorted(r.target_ref for r in doc.part.rels.values() if r.is_external) for doc in docs][1]
                with zipfile.ZipFile(a.before / 'renders' / (stem + '.docx')) as before, zipfile.ZipFile(a.after / 'renders' / (stem + '.docx')) as after:
                    for part in ['word/styles.xml', 'word/fontTable.xml', 'word/numbering.xml']:
                        assert before.read(part) == after.read(part)
                previews = [folder / 'word-preview' / (stem + '.pdf') for folder in [a.before, a.after]]
                # Compare every page's actual boxes, not LibreOffice's varying
                # PDF CreationDate metadata in the pdftotext XHTML head.
                assert geometry(previews[0]) == geometry(previews[1])
                assert fonts(previews[0]) == fonts(previews[1])
                paragraphs = verify_preview_paragraphs(docs[1], previews[1], BeautifulSoup(html[1], 'html.parser'))
                row = {'stem': stem, 'pages': [len(v[0]) for v in snapshots], 'missing_header_pages': missing,
                       'short_rows': [v['rows'] for v in parsed], 'long_pages': [v['long_pages'] for v in parsed],
                       'tail_together': [long_tail_together(v[0], source) for v, source in zip(snapshots, inputs)],
                       'word_unchanged': True, 'word_paragraphs_checked': paragraphs, 'bounds_findings': bounds,
                       'pdf_sha256': [sha(path) for path in paths], 'word_preview_sha256': [sha(path) for path in previews]}
                report['rows'].append(row)
                (a.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
                print(json.dumps({k: row[k] for k in ['stem', 'pages', 'missing_header_pages', 'tail_together']}), flush=True)
    report['selected_checks_passed'] = True
    (a.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
