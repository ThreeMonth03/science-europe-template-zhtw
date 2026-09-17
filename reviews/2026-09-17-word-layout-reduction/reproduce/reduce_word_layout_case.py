"""Make a Q1-Q5 diagnostic excerpt, not a full DMP or a template repair.

Retain the exact paragraph/table XML and section settings; remove bookmarks,
replace the cover with a diagnostic label, and omit Q6 onward. All other ZIP
parts remain byte-identical. The output must be a new directory.
"""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile
from lxml import etree as ET
from diagnose_word_import_layout import W, compact, q5_labels, sha, snapshot

ROOT = Path(__file__).resolve().parents[1]
LABEL = 'Diagnostic excerpt: Q1-Q5 only. Not a complete DMP.'


def text(node):
    return ''.join(t.text or '' for t in node.iter(W + 't'))


def no_bookmarks(node):
    result = copy.deepcopy(node)
    for child in list(result.iter()):
        if child.tag in (W + 'bookmarkStart', W + 'bookmarkEnd'):
            child.getparent().remove(child)
    return result


def retained_nodes(document):
    body = document.find(W + 'body')
    nodes = [n for n in body if n.tag in (W + 'p', W + 'tbl')]
    def heading(n, level, prefix):
        style = n.find(W + 'pPr/' + W + 'pStyle')
        return style is not None and style.get(W + 'val') == 'Heading' + str(level) and text(n).startswith(prefix)
    starts = [i for i, n in enumerate(nodes) if heading(n, 3, '1. ')]
    ends = [i for i, n in enumerate(nodes) if heading(n, 3, '6. ')]
    if len(starts) != 1 or len(ends) != 1 or not 0 < starts[0] < ends[0]:
        raise ValueError('Require unique Q1/Q6 headings')
    first = starts[0] - 1
    if not heading(nodes[first], 2, ''):
        raise ValueError('The section heading immediately before Q1 must be retained')
    keep = [no_bookmarks(n) for n in nodes[first:ends[0]]]
    sections = body.findall(W + 'sectPr')
    breaks = [n for n in body if n.tag == W + 'p' and any(b.get(W + 'type') == 'page' for b in n.iter(W + 'br'))]
    if len(sections) != 1 or len(breaks) != 1 or text(breaks[0]):
        raise ValueError('Require the single empty cover break and one section setup')
    return keep, copy.deepcopy(breaks[0]), copy.deepcopy(sections[0])


def reduce_case(source, target):
    q5_labels(source)  # Reject shapes outside the known bounded five-paragraph case.
    with zipfile.ZipFile(source) as old:
        document = ET.fromstring(old.read('word/document.xml'))
        keep, cover_break, section = retained_nodes(document)
        body = document.find(W + 'body')
        for child in list(body): body.remove(child)
        p = ET.SubElement(body, W + 'p'); r = ET.SubElement(p, W + 'r')
        ET.SubElement(r, W + 't').text = LABEL
        body.append(cover_break)
        for n in keep: body.append(n)
        body.append(section)
        with zipfile.ZipFile(target, 'x') as new:
            for info in old.infolist():
                data = old.read(info)
                if info.filename == 'word/document.xml':
                    data = ET.tostring(document, encoding='UTF-8', xml_declaration=True, standalone=True)
                new.writestr(copy.copy(info), data)
    return len(keep)


def prefix_geometry(pdf, section_heading):
    """Exact pre-Q5 body line positions, excluding cover and verified bottom page numbers."""
    root = ET.fromstring(subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-']))
    pages = root.findall('.//{*}page'); result = []
    for number, page in enumerate(pages, 1):
        if number == 1: continue
        lines = sorted(page.findall('.//{*}line'), key=lambda n: (float(n.get('yMin')), float(n.get('xMin'))))
        for line in lines:
            value = compact(''.join(line.itertext()))
            if value == compact(section_heading): return result
            if value == f'{number}/{len(pages)}' and float(line.get('yMin')) > float(page.get('height')) * .9:
                continue
            result.append(dict(page=number, text=value, **dict(line.attrib)))
    raise ValueError('Section 3 heading not found as a complete line')


def run(native_review, output):
    output.mkdir(parents=True, exist_ok=False)
    report = dict(diagnostic_not_native=True, release_acceptance=False, completed=False, rows=[],
                  script_sha256=sha(Path(__file__)),
                  helper_sha256=sha(Path(__file__).with_name('diagnose_word_import_layout.py')),
                  libreoffice_version=subprocess.check_output(['libreoffice', '--version'], text=True).strip())
    try:
        for language in ('chinese', 'english'):
            source = native_review / 'native' / ('metadata-partial-' + language + '.docx')
            baseline = native_review / 'word-preview' / ('metadata-partial-' + language + '.pdf')
            digest = sha(source); labels = q5_labels(source)
            target = output / ('reduced-' + language + '.docx')
            count = reduce_case(source, target)
            with zipfile.ZipFile(source) as old, zipfile.ZipFile(target) as new:
                unchanged_parts = [name for name in old.namelist() if name != 'word/document.xml']
                assert all(old.read(name) == new.read(name) for name in unchanged_parts)
                original = ET.fromstring(old.read('word/document.xml'))
                keep, _, _ = retained_nodes(original)
                index = next(i for i, n in enumerate(keep) if text(n) == labels[0])
                section_heading = text(keep[index - 1])
                actual = ET.fromstring(new.read('word/document.xml')).find(W + 'body')
                xml = lambda n: ET.tostring(n, method='c14n', exclusive=True)
                assert [xml(n) for n in list(actual)[2:-1]] == [xml(n) for n in keep]
            with tempfile.TemporaryDirectory(prefix='se-reduced-word-') as profile:
                subprocess.run(['libreoffice', '-env:UserInstallation=' + Path(profile).as_uri(),
                                '--headless', '--norestore', '--convert-to', 'pdf', '--outdir', str(output), str(target)],
                               capture_output=True, check=True, timeout=90)
            pdf = target.with_suffix('.pdf')
            before, after = snapshot(baseline, labels), snapshot(pdf, labels)
            row = dict(language=language, source_sha256=digest, source_unchanged=sha(source) == digest,
                       docx_sha256=sha(target), retained_body_blocks=count,
                       kept_paragraph_table_xml_unchanged=True, unchanged_zip_parts=unchanged_parts,
                       before=before, after=after,
                       reproduces_native_q5_pagination=before['q5_paragraph_page_spans'] == after['q5_paragraph_page_spans'],
                       pre_q5_line_geometry_unchanged=prefix_geometry(baseline, section_heading) == prefix_geometry(pdf, section_heading))
            report['rows'].append(row)
            print(json.dumps({key: row[key] for key in ('language', 'retained_body_blocks', 'reproduces_native_q5_pagination', 'pre_q5_line_geometry_unchanged')}), flush=True)
        assert all(row['source_unchanged'] and row['reproduces_native_q5_pagination'] and row['pre_q5_line_geometry_unchanged'] for row in report['rows'])
        report['completed'] = True
    except Exception as error:
        report['error'] = str(error); raise
    finally:
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-review', type=Path, default=ROOT / 'reviews/2026-09-17-storage-context-pagination/after')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); run(args.native_review, args.output)
