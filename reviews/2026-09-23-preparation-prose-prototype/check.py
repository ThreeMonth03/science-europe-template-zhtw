"""Bounded native prose projection; never strip or translate authored answers."""
from collections import Counter
import copy, itertools, json, re, subprocess, sys, zipfile
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString
from lxml import etree
from baseline_helpers import core, pdf, fonts, sha, raster

ROOT = Path(__file__).resolve().parent
UNITS = json.loads((ROOT / 'units.json').read_text())
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def compact(text): return ''.join(text.split())
def text_key(language, old): return ('old_' if old else '') + ('zh' if language == 'zh-Hant' else 'en')
def consume(text, key, allowed):
    for i in allowed:
        pattern = r'^\s*' + r'\s+'.join(re.escape(w) for w in UNITS[i][key].split())
        match = re.match(pattern, text)
        if match:
            return i, text[match.end():]
    return None, text
def fixed_prefix(text, key):
    unit, rest = consume(text, key, range(7))
    if unit is None: return [], text
    ids = [unit]
    if unit in range(3, 7):
        second, rest = consume(rest, key, [7, 8])
        if second is not None: ids.append(second)
    return ids, ''.join('[reviewed-unit-' + str(i) + ']' for i in ids) + rest
def html_view(data, language, old):
    soup = BeautifulSoup(data, 'html.parser'); counts = Counter()
    # Only direct, unmarked fixed-template paragraphs. Never descend into authored blocks.
    for p in soup.select('#q-how-data > .answer > p'):
        if p.attrs or not p.contents or not isinstance(p.contents[0], NavigableString): continue
        ids, text = fixed_prefix(str(p.contents[0]), text_key(language, old))
        if ids:
            counts.update(ids)
            p.contents[0].replace_with(text)
            # Only boundary indentation owned by this exact fixed paragraph may differ.
            if isinstance(p.contents[0], NavigableString): p.contents[0].replace_with(str(p.contents[0]).lstrip())
            if isinstance(p.contents[-1], NavigableString): p.contents[-1].replace_with(str(p.contents[-1]).rstrip())
    assert len(soup.select('#dmp-content > section.dmp-section')) == 6
    assert len(soup.select('#dmp-content > section.dmp-section > .question')) == 15
    return str(soup), counts
def html_pair(a, b, language, profile):
    old, oc = html_view(a, language, True); new, nc = html_view(b, language, False)
    assert oc == nc, 'Selected fixed facts changed'
    assert old == new, 'HTML outside permitted fixed prose changed'
    page = BeautifulSoup(b, 'html.parser')
    assert not page.select('p p, p div, p ul, p table')
    if profile == 'submission':
        assert not [n for n in page.select('.data-gap') if not n.find_parent(class_='answer-detail')]
    return oc
def word_view(data, language, old):
    tree = etree.fromstring(data); counts = Counter(); paragraphs = []
    for p in tree.findall('.//' + W + 'body/' + W + 'p'):
        raw = ''.join(p.itertext())
        ids, _ = fixed_prefix(raw, text_key(language, old))
        if not ids: continue
        counts.update(ids)
        # Fixed prose starts in the leading text run. Links and their original labels are separately exact.
        canonical = raw
        for i in ids:
            source = UNITS[i][text_key(language, old)]
            assert source in canonical
            canonical = canonical.replace(source, '[reviewed-unit-' + str(i) + ']', 1)
        paragraphs.append(dict(text=canonical.strip(), properties=etree.tostring(p.find(W + 'pPr')) if p.find(W + 'pPr') is not None else None,
            links=[etree.tostring(n) for n in p.findall('.//' + W + 'hyperlink')],
            run_properties=sorted(set(etree.tostring(n) for n in p.findall('.//' + W + 'rPr')))))
        p.clear(); p.text = '[owned-preparation-paragraph]'
    return etree.tostring(tree), paragraphs, counts
def word_pair(a, b, language, counts):
    with zipfile.ZipFile(a) as old, zipfile.ZipFile(b) as new:
        assert set(old.namelist()) == set(new.namelist())
        assert len(set(old.namelist())) == len(old.namelist()) == len(new.namelist())
        for name in old.namelist():
            x, y = old.read(name), new.read(name)
            if name == 'docProps/core.xml': x, y = core(x), core(y)
            elif name == 'word/document.xml':
                ox, op, oc = word_view(x, language, True); nx, np, nc = word_view(y, language, False)
                assert oc == nc == counts
                assert op == np, 'Word fixed paragraph content/style/link scope mismatch'
                x, y = ox, nx
            assert x == y, ('DOCX outside permitted prose changed', name)
def pdf_projection(text, language, old, counts):
    for i, count in counts.items():
        source = compact(UNITS[i][text_key(language, old)])
        assert text.count(source) == count, 'PDF missing or ambiguous fixed sentence'
        text = text.replace(source, '[reviewed-unit-' + str(i) + ']')
    return text
def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    renders = json.loads((ROOT / 'render-matrix.json').read_text())
    assert len(renders['rows']) == 56 and all(r['passed'] for r in renders['rows'])
    rows = []
    for case, language, profile in itertools.product(manifest['contexts'], ['en', 'zh-Hant'], ['review', 'submission']):
        name = '-'.join([case, language, profile]); a, b = [ROOT / arm / 'renders' / name for arm in ['baseline', 'candidate']]
        assert sha(ROOT / 'baseline/contexts' / (case + '.json')) == sha(ROOT / 'candidate/contexts' / (case + '.json')) == manifest['contexts'][case]
        counts = None
        for file in ['document.html', 'pdf-entry.html', 'word-entry.html']:
            selected = html_pair((a / file).read_bytes(), (b / file).read_bytes(), language, profile)
            if counts is None: counts = selected
            else: assert counts == selected
        word_pair(a / 'document.docx', b / 'document.docx', language, counts)
        metrics = {}
        for kind, file in [('pdf', 'document.pdf'), ('word_preview', 'word-preview/document.pdf')]:
            before, bt = pdf(a / file); after, at = pdf(b / file)
            assert fonts(a / file) == fonts(b / file), 'Fonts changed'
            # First require equal pagination; do not hide changed footers in a global cleanup.
            assert len(bt) == len(at), 'Pagination changed; requires a separate review'
            assert pdf_projection(''.join(bt), language, True, counts) == pdf_projection(''.join(at), language, False, counts), 'PDF text outside permitted prose changed'
            if not counts:
                assert before == after, 'Unchanged-content PDF geometry changed'
                assert all(raster(a / file, p) == raster(b / file, p) for p in range(1, len(at) + 1)), 'Unchanged-content page pixels changed'
            metrics[kind] = dict(before=len(bt), after=len(at), text_scope_checked=True, all_words_inside_page=True,
                                 unchanged_case_pixel_parity=not bool(counts))
        rows.append(dict(case={'P19': 'REAL-SNAPSHOT-A', 'P21': 'REAL-SNAPSHOT-B'}.get(case, case), language=language,
            profile=profile, passed=True, fixed_units_changed=sum(counts.values()), pages=metrics))
        print(json.dumps(dict(case=case, language=language, profile=profile, passed=True)), flush=True)
    report = dict(passed=True, release_acceptance=False, prototype_only=True, native_dsw_server=False, native_ms_word=False,
        package_sha256=manifest['package_sha256'], rows=rows, credentials_used=False, remote_writes=0,
        totals={kind: sum(r['pages'][kind]['after'] for r in rows) for kind in ['pdf', 'word_preview']})
    (ROOT / 'checks.json').write_text(json.dumps(report, indent=2))
if __name__ == '__main__': main()
