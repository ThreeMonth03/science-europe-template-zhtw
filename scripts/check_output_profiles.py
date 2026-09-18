"""Bounded native bilingual profile comparison and a separate internal checklist."""
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
from lxml import etree
from artifact_utils import sha
from check_budget_outputs import body
from check_q5_word_join_outputs import text_and_geometry
from check_word_short_budget_outputs import verify_preview_paragraphs
from check_word_rhythm_outputs import assert_styles
from check_budget_spacing_outputs import line_box_overlaps


def compact(value):
    return ''.join(value.split())


def replacements(review, language):
    result = []
    for node in review.select('#q-docs-metadata .reading-gap > p, '
                              '#q-store-backup > .answer > .storage-detail-limits > p, '
                              '#q-store-backup > .answer > .storage-detail-limits > ul > li, '
                              '#q-data-preservation > .answer > .reading-gap > [data-fact-id="preservation-selection-review"]'):
        result.append((compact(node.get_text()), '', node.name == 'li'))
    for node in review.select('p.data-gap[data-fact-id="quality-methods"]'):
        assert not node.find_parent(class_='answer-detail')
        name = node.strong.get_text()
        text = ('Quality control is planned for '+name+'.' if language == 'english'
                else '本計畫將對 '+name+' 進行品質管控。')
        result.append((compact(node.get_text()), compact(text), False))
    return result


def transformed(text, changes, list_marker=''):
    for (old, new, listed), count in Counter(changes).items():
        # Only two explicitly owned Q5 markers may disappear. Native PDF has
        # no marker here; this pinned LibreOffice preview extracts U+F0B7.
        key = (list_marker if listed else '') + old
        assert text.count(key) == count, ('Missing/ambiguous owned text', key, count, text.count(key))
        text = text.replace(key, new)
    return text


def pdf_marker_projection(values, soups, marker):
    """Pagination can move generated bullets in pdftotext's raw stream.

    This selected fixture contains no literal bullet characters in its HTML
    text. Check the exact marker-count delta (two removed Q5 items), then
    compare every remaining character. Never generalize this to arbitrary text.
    """
    markers = {'•', '◦', '\uf0b7', '\uf0a1'}
    assert all(not any(m in soup.get_text() for m in markers) for soup in soups)
    counts = [Counter(c for c in value if c in markers) for value in values]
    assert not counts[1]-counts[0], ('Unexpected added list markers', counts)
    assert counts[0]-counts[1] == Counter({marker: 2}), ('Expected only two Q5 markers removed', counts)
    return [''.join(c for c in value if c not in markers) for value in values], counts


def checklist(soup):
    rows = []
    for node in soup.select('[data-fact-id][data-status]'):
        if node.find_parent(class_='answer-detail'): continue
        if node.get('data-status') not in ('missing', 'needs-review', 'unmapped', 'partial'): continue
        if not (node.get('class') and 'data-gap' in node['class']) and not node.find_parent(class_='data-gap'):
            continue
        question = node.find_parent(class_='question')
        rows.append(dict(question=question.get('id') if question else None,
                         fact=node['data-fact-id'], status=node['data-status'], text=node.get_text(' ', strip=True)))
    for row in soup.select('#dmp-projects > .project > .project-details > tbody > tr'):
        cell = row.find('td', recursive=False)
        if cell and cell.get_text().strip() in ('Funding information has not been provided.', '尚未提供經費來源。'):
            rows.append(dict(question='project-overview', fact='funding', status='missing', text=cell.get_text().strip()))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--english', type=Path, required=True)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    sys.path[:0] = [str(a.english.resolve()/n) for n in ('scripts', 'tests')]
    from output_profile_contract import compare, CONTRACT
    report = dict(selected_checks_passed=False, release_acceptance=False, microsoft_word_acceptance=False,
        checker_sha256=sha(Path(__file__)), rows=[], limits=CONTRACT['not_yet_supported'],
        package_sha256={n: sha(a.build/n) for n in ('english.zip', 'chinese.zip')})
    target = a.output or a.build/'output-profiles-report.json'
    assert not target.exists()
    try:
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            roots = [a.build/'renders'/('profile-partial-'+profile+'-'+language) for profile in ('review', 'submission')]
            soups = [BeautifulSoup(path.with_suffix('.html').read_text(), 'html.parser') for path in roots]
            regions = [BeautifulSoup(str(s.select_one('#dmp-projects'))+str(s.select_one('#dmp-content')), 'html.parser') for s in soups]
            compare(*regions, language)
            assert len(soups[1].select('[data-fact-id="quality-methods"][data-status="partial"]')) == 2
            assert not soups[1].select('.data-gap'), 'This selected fixture should have no remaining system diagnostics'
            notes = checklist(soups[0]); assert len(notes) == 10, notes
            assert not checklist(soups[1])
            checklist_path = a.build/('internal-checklist-'+language+'.json')
            checklist_data = dict(scope='Partial pilot, not a whole-questionnaire completeness certificate',
                language=language, template_version='0.3.38', review_html_sha256=sha(roots[0].with_suffix('.html')),
                package_sha256=report['package_sha256'][language+'.zip'], items=notes)
            if checklist_path.exists():
                assert json.loads(checklist_path.read_text()) == checklist_data, 'Never overwrite different checklist evidence'
            else:
                checklist_path.write_text(json.dumps(checklist_data, ensure_ascii=False, indent=2)+'\n')
            changes = replacements(soups[0], language)
            docs = [Document(path.with_suffix('.docx')) for path in roots]
            values = [compact(''.join(t.text or '' for node in body(d) for t in node.iter(qn('w:t')))) for d in docs]
            assert transformed(values[0], changes) == values[1], 'Unexpected Word words/punctuation/order change'
            assert_styles(docs[1])
            links = lambda doc: sorted(r.target_ref for r in doc.part.rels.values() if r.is_external)
            assert links(docs[0]) == links(docs[1])
            with zipfile.ZipFile(roots[0].with_suffix('.docx')) as x, zipfile.ZipFile(roots[1].with_suffix('.docx')) as y:
                for part in ('word/styles.xml', 'word/fontTable.xml'):
                    assert x.read(part) == y.read(part), part
            row = dict(language=language, checklist_items=len(notes), remaining_system_diagnostics=0, artifacts={}, pagination={})
            for fmt in ('html', 'pdf', 'docx'):
                receipts = [json.loads(path.with_suffix('.'+fmt+'.fixture.json').read_text()) for path in roots]
                for key in ('recipe_sha256', 'events_sha256', 'km_sha256'):
                    assert receipts[0][key] == receipts[1][key]
                for profile, root, receipt in zip(('review', 'submission'), roots, receipts):
                    assert receipt['package_sha256'] == report['package_sha256'][language+'.zip']
                    assert receipt['output_profile'] == profile and receipt['format_uuid'] == CONTRACT['formats'][profile][fmt]
                    path = root.with_suffix('.'+fmt); row['artifacts'][str(path.relative_to(a.build))] = sha(path)
            marker = 'Information not provided: this is authored method text' if language == 'english' else '尚待補充：這是使用者填寫的方法說明'
            for name in ('native-pdf', 'word-preview'):
                pdfs = [path.with_suffix('.pdf') if name == 'native-pdf' else a.build/'word-preview'/(path.name+'.pdf') for path in roots]
                snapshots = [text_and_geometry(path, soup) for path, soup in zip(pdfs, soups)]
                texts, markers = pdf_marker_projection([s[0] for s in snapshots], soups, '\uf0b7' if name == 'word-preview' else '•')
                assert transformed(texts[0], changes) == texts[1], (language, name, 'Unexpected PDF text delta')
                assert compact(marker) in snapshots[1][0]
                assert compact('Original.csv') in snapshots[1][0]
                overlaps = [line_box_overlaps(bbox) for _, bbox in snapshots]
                assert overlaps[1] == overlaps[0], (language, name, 'New line-box overlap', overlaps)
                counts = [len(etree.fromstring(bbox).findall('.//{*}page')) for _, bbox in snapshots]
                assert counts[1] <= counts[0]
                row['pagination'][name] = dict(review=counts[0], submission=counts[1], line_box_overlaps=overlaps, list_marker_counts=markers)
                for path in pdfs: row['artifacts'][str(path.relative_to(a.build))] = sha(path)
            row['verified_word_preview_paragraphs'] = [verify_preview_paragraphs(d, a.build/'word-preview'/(r.name+'.pdf'), s) for d, r, s in zip(docs, roots, soups)]
            report['rows'].append(row)
            print(json.dumps(row['pagination']), flush=True)
        report['selected_checks_passed'] = True
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__': main()
