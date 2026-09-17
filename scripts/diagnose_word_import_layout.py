"""Read-only Q5 import/reflow experiment, NOT a template fix or release gate.

Run with system Python providing python3-uno. Each mode uses a private Writer
process/profile. Only diagnostic exports under a new output directory are saved.
Ordinary unit tests can import the pure helpers without LibreOffice/UNO installed.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
import zipfile

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
PROPERTIES = ('ParaStyleName', 'ParaKeepTogether', 'ParaSplit', 'ParaWidows',
              'ParaOrphans', 'ParaTopMargin', 'ParaBottomMargin')
MODES = ('direct', 'refresh', 'reformat', 'same-heading', 'same-policy',
         'same-intro', 'same-first-item', 'same-last-item', 'toggle-policy')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(value):
    return ''.join(value.split())


def q5_labels(source):
    with zipfile.ZipFile(source) as z:
        body = ET.fromstring(z.read('word/document.xml')).find(W + 'body')
    paragraphs = [(p, ''.join(t.text or '' for t in p.iter(W + 't')))
                  for p in body if p.tag == W + 'p']
    def heading(p, text, number):
        style = p.find(W + 'pPr/' + W + 'pStyle')
        return text.startswith(f'{number}. ') and style is not None and style.get(W + 'val') == 'Heading3'
    starts = [i for i, (p, text) in enumerate(paragraphs) if heading(p, text, 5)]
    ends = [i for i, (p, text) in enumerate(paragraphs) if heading(p, text, 6)]
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise ValueError('Require unique, ordered Q5/Q6 headings')
    selected = paragraphs[starts[0]:ends[0]]
    labels = [text for _, text in selected]
    if len(labels) != 5 or len(set(map(compact, labels))) != 5 or any(not compact(t) for t in labels):
        raise ValueError('Only the five-paragraph bounded Q5 fixture is supported')
    style_nodes = [p.find(W + 'pPr/' + W + 'pStyle') for p, _ in selected]
    styles = [node.get(W + 'val') if node is not None else None for node in style_nodes]
    if styles != ['Heading3', 'PilotLead', 'PilotLead', 'PilotListLead', 'Compact']:
        raise ValueError('Unexpected Q5 styles; do not silently broaden the experiment')
    return labels


def paragraph_spans(pages, labels):
    """Locate complete paragraphs, preserving split-page results and ambiguity."""
    pages = [compact(p) for p in pages]
    joined = ''.join(pages)
    boundaries = [0]
    for page in pages:
        boundaries.append(boundaries[-1] + len(page))
    spans = []
    for label in labels:
        text = compact(label)
        if not text or joined.count(text) != 1:
            raise ValueError('Missing or ambiguous complete Q5 paragraph')
        start = joined.index(text); end = start + len(text)
        spans.append([i + 1 for i in range(len(pages))
                      if start < boundaries[i + 1] and end > boundaries[i]])
    return spans


def same_page(spans):
    return bool(spans) and all(len(span) == 1 for span in spans) and len({span[0] for span in spans}) == 1


def text_comparison(rows):
    key = 'full_text_without_whitespace_and_verified_footers_sha256'
    original = next(row[key] for row in rows if row['mode'] == 'direct')
    memory = [row for row in rows if not row['mode'].endswith('-reopened')]
    return dict(all_exports_same_normalized_text=all(row[key] == original for row in rows),
                all_memory_exports_same_normalized_text=all(row[key] == original for row in memory),
                reopened_text_equals_direct={row['mode']: row[key] == original for row in rows if row['mode'].endswith('-reopened')})


def clean_pages(raw, bbox):
    """Strip only the exact page/total footer verified in the page's bottom 10%."""
    pages = raw.split('\f')
    if not pages[-1].strip(): pages.pop()
    geometry = ET.fromstring(bbox).findall('.//{*}page')
    if len(pages) != len(geometry): raise ValueError('PDF page count mismatch')
    result = []
    for number, (text, page) in enumerate(zip(pages, geometry), 1):
        footer = f'{number}/{len(pages)}'
        matches = [line for line in page.findall('.//{*}line') if compact(''.join(line.itertext())) == footer]
        lines = [line for line in text.splitlines() if line.strip()]
        if matches:
            if len(matches) != 1 or float(matches[0].get('yMin')) <= float(page.get('height')) * .9:
                raise ValueError('Ambiguous or misplaced footer')
            if sum(compact(line) == footer for line in lines) != 1:
                raise ValueError('Ambiguous footer text')
            lines = [line for line in lines if compact(line) != footer]
        elif number != 1:
            raise ValueError('Only the cover may omit the footer')
        result.append(compact(''.join(lines)))
    return result


def snapshot(pdf, labels):
    raw = subprocess.check_output(['pdftotext', '-raw', str(pdf), '-'], text=True)
    bbox = subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-'])
    pages = clean_pages(raw, bbox)
    spans = paragraph_spans(pages, labels)
    return dict(pages=len(pages), q5_paragraph_page_spans=spans, q5_together=same_page(spans),
                full_text_without_whitespace_and_verified_footers_sha256=hashlib.sha256(''.join(pages).encode()).hexdigest(),
                pdf_sha256=sha(pdf))


def prop(name, value):
    import uno
    item = uno.createUnoStruct('com.sun.star.beans.PropertyValue')
    item.Name = name; item.Value = value
    return item


@contextmanager
def document(source):
    import uno
    with tempfile.TemporaryDirectory(prefix='se-word-layout-') as folder:
        pipe = 'se_word_' + uuid.uuid4().hex
        process = subprocess.Popen(['libreoffice', '-env:UserInstallation=' + Path(folder).as_uri(),
                                    '--headless', '--norestore', '--nodefault', '--nofirststartwizard',
                                    '--accept=pipe,name=' + pipe + ';urp;StarOffice.ComponentContext'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        desktop = doc = None
        try:
            local = uno.getComponentContext()
            resolver = local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver', local)
            deadline = time.monotonic() + 15
            while True:
                try:
                    context = resolver.resolve('uno:pipe,name=' + pipe + ';urp;StarOffice.ComponentContext')
                    break
                except Exception:
                    if time.monotonic() >= deadline or process.poll() is not None: raise
                    time.sleep(.1)
            desktop = context.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop', context)
            doc = desktop.loadComponentFromURL(source.resolve().as_uri(), '_blank', 0,
                (prop('Hidden', True), prop('ReadOnly', True),
                 prop('MacroExecutionMode', uno.getConstantByName('com.sun.star.document.MacroExecMode.NEVER_EXECUTE')),
                 prop('UpdateDocMode', uno.getConstantByName('com.sun.star.document.UpdateDocMode.NO_UPDATE'))))
            if doc is None: raise RuntimeError('Writer did not open the diagnostic input')
            yield doc
        finally:
            try:
                if doc is not None: doc.close(True)
            finally:
                try:
                    if desktop is not None: desktop.terminate()
                finally:
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        try: process.wait(timeout=5)
                        except subprocess.TimeoutExpired: process.kill(); process.wait()


def paragraphs(doc, labels):
    found = [[] for _ in labels]
    enumeration = doc.Text.createEnumeration()
    while enumeration.hasMoreElements():
        p = enumeration.nextElement()
        if p.supportsService('com.sun.star.text.Paragraph'):
            for i, label in enumerate(labels):
                if p.String == label: found[i].append(p)
    if any(len(items) != 1 for items in found): raise ValueError('UNO paragraph identity mismatch')
    return [items[0] for items in found]


def properties(paragraphs):
    return [{key: dict(value=p.getPropertyValue(key), state=str(p.getPropertyState(key)))
             for key in PROPERTIES} for p in paragraphs]


def mutate(doc, selected, mode):
    if mode == 'refresh': doc.refresh()
    elif mode == 'reformat': doc.reformat()
    elif mode == 'toggle-policy':
        old = selected[1].ParaKeepTogether
        selected[1].ParaKeepTogether = not old; selected[1].ParaKeepTogether = old
    elif mode.startswith('same-'):
        index = {'heading': 0, 'policy': 1, 'intro': 2, 'first-item': 3, 'last-item': 4}[mode[5:]]
        p = selected[index]; p.ParaKeepTogether = p.ParaKeepTogether
    elif mode != 'direct': raise ValueError('Unknown experiment mode')


def run(source, output):
    labels = q5_labels(source); digest = sha(source)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(diagnostic_not_native=True, release_acceptance=False, source_sha256=digest,
                  source_name=source.name, script_sha256=sha(Path(__file__)),
                  libreoffice_version=subprocess.check_output(['libreoffice', '--version'], text=True).strip(),
                  rows=[], completed=False, source_unchanged=False,
                  limits=['Synthetic bounded Q5 only; not all DMPs or Microsoft Word',
                          'Memory edits and saved diagnostic copies are NOT native DSW outputs',
                          'Text equality ignores whitespace and verified page footers, not punctuation'])
    try:
        for mode in MODES:
            with document(source) as doc:
                selected = paragraphs(doc, labels); before = properties(selected)
                mutate(doc, selected, mode)
                after = properties(selected)
                pdf = output / (mode + '.pdf')
                doc.storeToURL(pdf.resolve().as_uri(), (prop('FilterName', 'writer_pdf_Export'),))
                row = dict(mode=mode, before_properties=before, after_properties=after, **snapshot(pdf, labels))
                if mode in ('direct', 'same-policy'):
                    target = output / (mode + '-saved.docx')
                    doc.storeToURL(target.resolve().as_uri(), (prop('FilterName', 'Office Open XML Text'),))
                    row['saved_docx_sha256'] = sha(target)
                report['rows'].append(row)
                print(json.dumps(dict(mode=mode, pages=row['pages'], q5_spans=row['q5_paragraph_page_spans'])), flush=True)
        for mode in ('direct', 'same-policy'):
            with document(output / (mode + '-saved.docx')) as doc:
                pdf = output / (mode + '-reopened.pdf')
                doc.storeToURL(pdf.resolve().as_uri(), (prop('FilterName', 'writer_pdf_Export'),))
                row = dict(mode=mode + '-reopened', imported_properties=properties(paragraphs(doc, labels)), **snapshot(pdf, labels))
                report['rows'].append(row)
                print(json.dumps(dict(mode=row['mode'], pages=row['pages'], q5_spans=row['q5_paragraph_page_spans'])), flush=True)
        report.update(text_comparison(report['rows']))
        report['unmodified_docx_q5_together'] = report['rows'][0]['q5_together']
        report['saved_policy_copy_q5_together_after_reopen'] = report['rows'][-1]['q5_together']
        # Round-tripped copies are separate observations, never a content-preserving
        # fix. Keep any text mismatch visible rather than stripping extra glyphs.
        if not report['all_memory_exports_same_normalized_text']: raise ValueError('Memory-only export text changed')
        report['completed'] = True
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        report['source_unchanged'] = sha(source) == digest
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        if not report['source_unchanged']: raise RuntimeError('Original DOCX changed')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.source, args.output)
