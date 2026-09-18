"""Non-release DOCX A/B trials on exact native profile inputs; never overwrite them."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile
from lxml import etree as E
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_word_short_budget_outputs import verify_preview_paragraphs
from docx import Document

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
PROFILES = ('baseline', 'direct-keep', 'summary-body', 'custom-label',
            'label-no-outline', 'summary-keep', 'joined-label')


def text(node): return ''.join(node.itertext()) if node.tag == W+'t' else ''.join(n.text or '' for n in node.iter(W+'t'))


def select(document):
    body = document.find(W+'body'); nodes = [n for n in body if n.tag not in (W+'bookmarkStart', W+'bookmarkEnd')]
    start = [i for i, n in enumerate(nodes) if n.tag == W+'p' and text(n).startswith('11. ')]
    assert len(start) == 1
    i = start[0]; heading, label, summary = nodes[i:i+3]
    assert heading.find(W+'pPr/'+W+'pStyle').get(W+'val') == 'Heading3'
    assert label.find(W+'pPr/'+W+'pStyle').get(W+'val') == 'Heading5'
    assert summary.find(W+'pPr/'+W+'pStyle').get(W+'val') == 'FirstParagraph'
    assert summary.tag == W+'p' and 0 < len(text(summary)) < 400
    assert label.getnext() is summary, 'Do not merge across bookmarks or other intervening nodes'
    return heading, label, summary


def c14n(node): return E.tostring(node, method='c14n', exclusive=True)


def geometry(pdf):
    value = subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-'])
    return [c14n(page) for page in E.fromstring(value).findall('.//{*}page')]


def validate_change(before, styles, after, revised_styles, profile):
    """Restore only the designated Q11 changes; reject any unrelated XML delta."""
    old_heading, old_label, old_summary = select(before)
    restored = copy.deepcopy(after)
    heading = [p for p in restored.find(W+'body') if p.tag == W+'p' and text(p).startswith('11. ')]
    assert len(heading) == 1
    heading = heading[0]
    label = heading.getnext()
    while label.tag in (W+'bookmarkStart', W+'bookmarkEnd'): label = label.getnext()
    summary = label.getnext()
    expected_styles = copy.deepcopy(styles)
    if profile == 'direct-keep':
        for node in (heading, label):
            props = node.find(W+'pPr')
            for key in ('keepNext', 'keepLines'):
                values = props.findall(W+key)
                assert len(values) == 1 and values[0].attrib == {W+'val': '1'}
                props.remove(values[0])
    elif profile == 'summary-body':
        style = summary.find(W+'pPr/'+W+'pStyle')
        assert style.get(W+'val') == 'BodyText'
        style.set(W+'val', 'FirstParagraph')
    elif profile in ('custom-label', 'label-no-outline'):
        style = label.find(W+'pPr/'+W+'pStyle')
        assert style.get(W+'val') == 'PilotPreservationHeading'
        style.set(W+'val', 'Heading5')
        clone = copy.deepcopy(next(n for n in styles if n.get(W+'styleId') == 'Heading5'))
        clone.set(W+'styleId', 'PilotPreservationHeading'); clone.set(W+'customStyle', '1')
        clone.find(W+'name').set(W+'val', 'Pilot Preservation Heading')
        if profile == 'label-no-outline': clone.find(W+'pPr/'+W+'outlineLvl').set(W+'val', '9')
        expected_styles.append(clone)
    elif profile == 'summary-keep':
        for key in ('keepNext', 'keepLines'):
            props = summary.find(W+'pPr'); values = props.findall(W+key)
            assert len(values) == 1 and values[0].attrib == {W+'val': '1'}
            props.remove(values[0])
    elif profile == 'joined-label':
        # Independently split the merged runs again, including every original
        # run property and original summary paragraph property.
        label_parts = list(old_label); summary_parts = [n for n in old_summary if n.tag != W+'pPr']
        assert len(label) == len(label_parts)+1+len(summary_parts)
        separator = label[len(label_parts)]
        assert c14n(separator) == c14n(E.fromstring(('<w:r xmlns:w="'+W[1:-1]+'"><w:br/></w:r>').encode()))
        for actual, expected in zip(list(label)[len(label_parts)+1:], summary_parts):
            assert c14n(actual) == c14n(expected)
        for child in list(label)[len(label_parts):]: label.remove(child)
        props = label.find(W+'pPr'); style = props.find(W+'pStyle')
        assert style.get(W+'val') == 'BodyText'; style.set(W+'val', 'Heading5')
        keeps = props.findall(W+'keepLines')
        assert len(keeps) == 1 and keeps[0].attrib == {W+'val': '1'}; props.remove(keeps[0])
        for run, original in zip(label.findall(W+'r'), old_label.findall(W+'r')):
            run_props = run.find(W+'rPr'); bolds = run_props.findall(W+'b')
            assert len(bolds) == 1 and bolds[0].attrib == {W+'val': '1'}; run_props.remove(bolds[0])
            if original.find(W+'rPr') is None:
                assert not len(run_props) and not run_props.attrib; run.remove(run_props)
        label.addnext(copy.deepcopy(old_summary))
    else: assert profile == 'baseline'
    assert c14n(restored) == c14n(before), 'Unreviewed document XML changed'
    assert c14n(revised_styles) == c14n(expected_styles), 'Unreviewed style XML changed'


def transform(document, styles, profile):
    result, revised_styles = copy.deepcopy(document), copy.deepcopy(styles)
    heading, label, summary = select(result)
    if profile == 'direct-keep':
        for node in (heading, label):
            props = node.find(W+'pPr')
            for key in ('keepNext', 'keepLines'):
                assert props.find(W+key) is None
                E.SubElement(props, W+key, {W+'val': '1'})
    elif profile == 'summary-body':
        summary.find(W+'pPr/'+W+'pStyle').set(W+'val', 'BodyText')
    elif profile in ('custom-label', 'label-no-outline'):
        style = next(n for n in styles if n.get(W+'styleId') == 'Heading5')
        clone = copy.deepcopy(style); clone.set(W+'styleId', 'PilotPreservationHeading')
        clone.set(W+'customStyle', '1'); clone.find(W+'name').set(W+'val', 'Pilot Preservation Heading')
        if profile == 'label-no-outline':
            outline = clone.find(W+'pPr/'+W+'outlineLvl')
            assert outline is not None
            outline.set(W+'val', '9')
        revised_styles.append(clone)
        label.find(W+'pPr/'+W+'pStyle').set(W+'val', 'PilotPreservationHeading')
    elif profile == 'summary-keep':
        props = summary.find(W+'pPr')
        for key in ('keepNext', 'keepLines'):
            assert props.find(W+key) is None
            E.SubElement(props, W+key, {W+'val': '1'})
    elif profile == 'joined-label':
        assert all(n.tag in (W+'pPr', W+'r') for n in label)
        props = label.find(W+'pPr')
        props.find(W+'pStyle').set(W+'val', 'BodyText')
        E.SubElement(props, W+'keepLines', {W+'val': '1'})
        for run in label.findall(W+'r'):
            run_props = run.find(W+'rPr')
            if run_props is None:
                run_props = E.Element(W+'rPr'); run.insert(0, run_props)
            assert run_props.find(W+'b') is None
            E.SubElement(run_props, W+'b', {W+'val': '1'})
        E.SubElement(E.SubElement(label, W+'r'), W+'br')
        for node in list(summary):
            if node.tag != W+'pPr': label.append(node)
        summary.getparent().remove(summary)
    else: assert profile == 'baseline'
    assert [n.text for n in document.iter(W+'t')] == [n.text for n in result.iter(W+'t')]
    validate_change(document, styles, result, revised_styles, profile)
    return result, revised_styles


def locate(pdf, strings):
    pages = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True).split('\f')[:-1]
    compact = lambda value: ''.join(value.split())
    result = [[i for i, p in enumerate(pages, 1) if compact(s) in compact(p)] for s in strings]
    assert all(len(v) == 1 for v in result), result
    return len(pages), [v[0] for v in result]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=Path('reviews/2026-09-18-output-profiles'))
    p.add_argument('--trials', nargs='+', choices=PROFILES, default=PROFILES)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    assert not a.output.exists(); a.output.mkdir(parents=True)
    report = dict(completed=False, release_acceptance=False, native_export=False, microsoft_word_acceptance=False,
        rows=[], checker_sha256=sha(Path(__file__)),
        libreoffice_version=subprocess.check_output(['libreoffice', '--version'], text=True).strip(),
        limits=['Exact frozen native DOCX modified for diagnosis, not a template implementation',
                'The joined-label trial removes one dataset Heading5; Q11 Heading3 is retained',
                'Only this short synthetic summary; no whole-questionnaire pagination guarantee'])
    try:
        for language in ('english', 'chinese'):
            for mode in ('review', 'submission'):
                stem = 'profile-partial-'+mode+'-'+language
                source = a.source/'native'/(stem+'.docx')
                soup = BeautifulSoup((a.source/'question-content'/(stem+'.html')).read_text(), 'html.parser')
                with zipfile.ZipFile(source) as z:
                    original = E.fromstring(z.read('word/document.xml')); styles = E.fromstring(z.read('word/styles.xml'))
                    heading, label, summary = select(original)
                    for profile in a.trials:
                        revised, revised_styles = transform(original, styles, profile)
                        docx = a.output/(stem+'-'+profile+'.docx')
                        with zipfile.ZipFile(docx, 'w', compression=zipfile.ZIP_DEFLATED) as target:
                            for part in z.namelist():
                                content = E.tostring(revised, xml_declaration=True, encoding='UTF-8', standalone=True) if part == 'word/document.xml' else E.tostring(revised_styles, xml_declaration=True, encoding='UTF-8', standalone=True) if part == 'word/styles.xml' else z.read(part)
                                target.writestr(part, content)
                        with tempfile.TemporaryDirectory(prefix='se-q11-rehearsal-') as temp:
                            r = subprocess.run(['libreoffice', '-env:UserInstallation='+Path(temp).as_uri(), '--headless', '--convert-to', 'pdf', '--outdir', str(a.output), str(docx)], capture_output=True, text=True, timeout=120)
                        pdf = docx.with_suffix('.pdf'); assert r.returncode == 0 and pdf.exists(), r.stderr
                        count, positions = locate(pdf, [text(heading), text(summary)])
                        checked = verify_preview_paragraphs(Document(docx), pdf, soup)
                        row = dict(language=language, mode=mode, trial=profile, pages=count, q11_heading_summary_pages=positions,
                            together=len(set(positions)) == 1, paragraphs_checked=checked, source_sha256=sha(source), docx_sha256=sha(docx), pdf_sha256=sha(pdf),
                            exact_xml_delta_checked=True, dataset_heading5_removed=profile=='joined-label')
                        if profile == 'baseline':
                            prior = a.source/'word-preview'/(stem+'.pdf')
                            assert geometry(prior) == geometry(pdf), 'Baseline preview geometry drift'
                            row['native_preview_geometry_identical']=True
                        report['rows'].append(row); print(json.dumps(row), flush=True)
        report['completed'] = True
    finally: (a.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__': main()
