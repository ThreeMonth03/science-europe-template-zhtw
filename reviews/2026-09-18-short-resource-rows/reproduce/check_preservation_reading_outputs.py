"""Same-fixture native Word label/summary delta, with unchanged fallback controls."""
import argparse
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from lxml import etree as E
from artifact_utils import sha
from check_budget_outputs import body, question_body
from check_narrative_outputs import page_bounds
from check_word_rhythm_outputs import assert_styles, compare_questions, inspect_preview
from check_word_short_budget_outputs import verify_preview_paragraphs
from rehearse_profile_pagination import geometry, locate, select, text, W


def body_xml(document):
    root = E.Element(W+'document'); content = E.SubElement(root, W+'body')
    for node in body(document): content.append(copy.deepcopy(node))
    return E.tostring(root)


def style_archive(value):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive: archive.writestr('word/styles.xml', value)
    return stream.getvalue()


def hashes(folder, stem):
    names = [folder/'renders'/(stem+'.'+fmt+extra)
        for fmt in ('html', 'pdf', 'docx') for extra in ('', '.fixture.json')]
    names.append(folder/'word-preview'/(stem+'.pdf'))
    return {str(p.relative_to(folder)): sha(p) for p in names}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'prior-controls', 'prior-profile', 'english', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--cases', nargs='+', choices=('empty', 'preservation-partial', 'profile-partial'),
        default=['empty', 'preservation-partial', 'profile-partial'])
    a = p.parse_args(); assert not a.output.exists()
    assert len(a.cases) == len(set(a.cases))
    sys.path.insert(0, str(a.english.resolve()/'scripts'))
    from preservation_reading_contract import prior_reference, word_content, STYLE
    report = dict(selected_checks_passed=False, release_acceptance=False, microsoft_word_acceptance=False,
        version='0.3.39', cases=a.cases, rows=[], checker_sha256=sha(Path(__file__)),
        contract_sha256=sha(a.english/'scripts/preservation_reading_contract.py'),
        package_sha256={n: sha(a.build/n) for n in ('english.zip', 'chinese.zip')},
        helper_sha256={n: sha(Path(__file__).with_name(n)) for n in (
            'artifact_utils.py', 'check_budget_outputs.py', 'check_narrative_outputs.py',
            'check_word_rhythm_outputs.py', 'check_word_short_budget_outputs.py', 'rehearse_profile_pagination.py')},
        limits=['Only the explicitly selected public synthetic fixtures, both languages and both profiles; not all DMPs',
            'Whole Word body XML checked; only selected Q11 label merge and bookmark relocation allowed',
            'Cover version/date metadata excluded from body comparisons',
            'PDF geometry differences are diagnostic, not silently accepted as exact equality',
            'LibreOffice preview is not Microsoft Word acceptance',
            'Tables-only isolated worker; stock Markdown-table support remains a separate blocker'])
    try:
        for case in a.cases:
            prior = a.prior_profile if case == 'profile-partial' else a.prior_controls
            prior_packages = {n: sha(prior/n) for n in ('english.zip', 'chinese.zip')}
            for profile in ('review', 'submission'):
                for language in ('english', 'chinese'):
                    stem = case+'-'+profile+'-'+language
                    old, new = [folder/'renders'/stem for folder in (prior, a.build)]
                    for fmt in ('html', 'pdf', 'docx'):
                        receipts = [json.loads(path.with_suffix('.'+fmt+'.fixture.json').read_text()) for path in (old, new)]
                        for key in ('recipe_sha256', 'events_sha256', 'km_sha256'):
                            assert receipts[0][key] == receipts[1][key], (stem, fmt, key)
                        assert receipts[0]['package_sha256'] == prior_packages[language+'.zip']
                        assert receipts[1]['package_sha256'] == report['package_sha256'][language+'.zip']
                    soups = [BeautifulSoup(path.with_suffix('.html').read_text(), 'html.parser') for path in (old, new)]
                    count = compare_questions(*soups)
                    docs = [Document(path.with_suffix('.docx')) for path in (old, new)]
                    assert_styles(docs[1]); eligible = case == 'profile-partial'; anchors = []
                    selected = [node for node in docs[1].element.body if node.tag == W+'p'
                        and node.find(W+'pPr/'+W+'pStyle') is not None
                        and node.find(W+'pPr/'+W+'pStyle').get(W+'val') == STYLE]
                    assert len(selected) == int(eligible), (stem, 'Unexpected eligible paragraph count')
                    if eligible:
                        heading, label, summary = select(docs[0].element)
                        mark = label.getprevious(); assert mark.tag == W+'bookmarkStart'
                        anchors = [mark.get(W+'name')]
                        assert [n.get(W+'name') for n in selected[0].iter(W+'bookmarkStart')] == anchors
                    word_content(body_xml(docs[0]), body_xml(docs[1]), anchors)
                    links = lambda d: sorted(r.target_ref for r in d.part.rels.values() if r.is_external)
                    assert links(docs[0]) == links(docs[1]), 'External link changed'
                    with zipfile.ZipFile(old.with_suffix('.docx')) as before, zipfile.ZipFile(new.with_suffix('.docx')) as after:
                        prior_reference(*[style_archive(z.read('word/styles.xml')) for z in (before, after)])
                        for part in ('word/numbering.xml', 'word/fontTable.xml'):
                            assert before.read(part) == after.read(part), part
                    row = dict(case=case, profile=profile, language=language, question_comparisons=count,
                        merged_word_paragraphs=len(selected), exact_word_body_delta=True,
                        prior_package_sha256=prior_packages,
                        prior_artifact_sha256=hashes(prior, stem), artifact_sha256=hashes(a.build, stem))
                    for kind, paths in (
                        ('pdf', [old.with_suffix('.pdf'), new.with_suffix('.pdf')]),
                        ('word', [folder/'word-preview'/(stem+'.pdf') for folder in (prior, a.build)])):
                        assert question_body(paths[0], soups[0]) == question_body(paths[1], soups[1]), (stem, kind, 'Body text changed')
                        pages = [page_bounds(path) for path in paths]
                        assert pages[0] == pages[1], (stem, kind, 'Page count changed', pages)
                        row[kind+'_pages'] = pages[1]
                        geometries = [geometry(path)[1:] for path in paths]
                        row[kind+'_changed_body_geometry_pages'] = [i for i, pair in enumerate(zip(*geometries), 2) if pair[0] != pair[1]]
                        if kind == 'word' and not eligible:
                            assert not row[kind+'_changed_body_geometry_pages'], (stem, 'Fallback pagination changed')
                    preview = a.build/'word-preview'/(stem+'.pdf')
                    inspect_preview(preview)
                    row['preview_paragraphs_checked'] = verify_preview_paragraphs(docs[1], preview, soups[1])
                    if eligible:
                        strings = [text(heading), text(summary)]
                        row['prior_q11_heading_summary_pages'] = locate(prior/'word-preview'/(stem+'.pdf'), strings)[1]
                        row['q11_heading_summary_pages'] = locate(preview, strings)[1]
                        assert len(set(row['q11_heading_summary_pages'])) == 1, (stem, 'Q11 still split')
                        if language == 'chinese' and profile == 'submission':
                            assert row['prior_q11_heading_summary_pages'] == [4, 5]
                            assert row['q11_heading_summary_pages'] == [5, 5]
                    row['passed'] = True; report['rows'].append(row)
                    print(json.dumps({k: row[k] for k in ('case', 'profile', 'language', 'merged_word_paragraphs', 'word_pages')}), flush=True)
        report['selected_checks_passed'] = len(report['rows']) == 4*len(a.cases)
    except Exception as error:
        report['failure'] = str(error); raise
    finally:
        a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__': main()
