"""Native A/B checks. Never emit project text in public summaries."""
import copy
from collections import Counter
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
from bs4 import BeautifulSoup
from lxml import etree

os.umask(0o077)
ROOT = Path(__file__).resolve().parent
EN = Path('/home/trc/Downloads/science-europe-template')
ZH = Path('/home/trc/Downloads/science-europe-template-zhtw')
PRIOR = Path('/home/trc/.local/share/dsw-followup-integration.tAHjaD')
sys.path.insert(0, str(EN / 'experiments/reuse-summary'))
import probe
WORDS = json.loads((ZH / 'experiments/reuse-summary/translations.json').read_text())


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def compact(text): return ''.join(text.split())


def word_question(xml, start='q-how-data', end='q-what-data'):
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    blocks = list(xml.find('w:body', ns))
    def position(name):
        indices = [index for index, block in enumerate(blocks) if block.xpath('descendant-or-self::w:bookmarkStart[@w:name=$name]', namespaces=ns, name=name)]
        assert len(indices) == 1, 'Missing/ambiguous Word question boundary'
        return indices[0]
    first, last = position(start), position(end)
    assert first < last
    question = etree.Element('question')
    for block in blocks[first:last]: question.append(copy.deepcopy(block))
    return question


def layout(path):
    tree = etree.fromstring(subprocess.check_output(['pdftotext', '-bbox-layout', str(path), '-']))
    pages = tree.findall('.//{*}page')
    assert pages, 'Vacuous PDF page inventory'
    for page in pages:
        words = page.findall('.//{*}word'); assert words, 'Empty PDF page'
        for word in words:
            assert 0 <= float(word.get('xMin')) <= float(word.get('xMax')) <= float(page.get('width')) + .5
            assert 0 <= float(word.get('yMin')) <= float(word.get('yMax')) <= float(page.get('height')) + .5
    return tree, pages, compact(''.join(tree.itertext()))


def expected(context, locale):
    replies = {p: r['value']['value'] for p, r in context['project']['replies'].items()}
    result = {}
    if replies.get(probe.PRE) != probe.IDS['preexistingYesAUuid']: return result
    for item in replies.get(probe.LIST, []):
        use = probe.path(probe.LIST, item, 'nrefDataUseQUuid')
        if replies.get(use) != probe.IDS['nrefDataUseYesAUuid']: continue
        prefix = probe.path(use, 'nrefDataUseYesAUuid')
        facts = []
        for fact, (question, options) in probe.FIELDS.items():
            value = replies.get(probe.path(prefix, question))
            selected = next((name for name in options if probe.IDS[name] == value), None)
            if selected:
                text = options[selected]; facts.append((fact, WORDS[text] if locale == 'zh-Hant' else text))
        detail = probe.path(prefix, 'nrefDataConditionsQUuid', 'nrefDataConditionsOtherAUuid', 'nrefDataConditionsOtherQUuid')
        other = replies.get(probe.path(prefix, 'nrefDataConditionsQUuid')) == probe.IDS['nrefDataConditionsOtherAUuid']
        result[item] = dict(facts=facts, detail=detail if other else None, filled=bool(str(replies.get(detail, '')).strip()))
    return result


def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    oracle = json.loads((ROOT / 'authored-oracle.json').read_text())
    assert sha(PRIOR / 'evidence-sha256.json') == manifest['prior_seal']
    inventory = json.loads((PRIOR / 'evidence-sha256.json').read_text())['files']
    assert all(sha(PRIOR / row['path']) == row['sha256'] for row in inventory)
    renders = json.loads((ROOT / 'renders.json').read_text())
    assert len(renders) == 56 and all(r['passed'] for r in renders)
    previews = json.loads((ROOT / 'previews.json').read_text())
    assert len(previews) == 44 and all(r['passed'] for r in previews)
    rows = []
    for case, locale, profile in itertools.product(manifest['cases'], ['en', 'zh-Hant'], ['review', 'submission']):
        folder = f'{case}-{locale}-{profile}'
        a, b = [ROOT / arm / 'renders' / folder for arm in ['baseline', 'candidate']]
        context_path = ROOT / 'candidate/contexts' / (case + '.json')
        assert sha(context_path) == manifest['contexts'][case]
        assert sha(context_path) == sha(ROOT / 'baseline/contexts' / context_path.name)
        context = json.loads(context_path.read_text())
        exp = expected(context, locale)
        all_facts = []; summary_counts = []; authored_fragments = Counter()
        for filename in ['document.html', 'pdf-entry.html', 'word-entry.html']:
            old, new = [BeautifulSoup((p / filename).read_text(), 'html.parser') for p in [a, b]]
            assert len(new.select('.question')) == 15 and len(new.select('.dmp-section')) == 6
            old_questions, new_questions = [s.select('.question') for s in [old, new]]
            assert [probe.dom(q) for q in old_questions[1:]] == [probe.dom(q) for q in new_questions[1:]], 'Q2–15 drift'
            for selector in ['[data-fact-id="reuse-purpose"]', '[data-fact-id="dataset-source"]', '[data-fact-id="reuse-decision"]']:
                assert [probe.dom(n) for n in old.select('#q-how-data ' + selector)] == [probe.dom(n) for n in new.select('#q-how-data ' + selector)]
            assert len(new.select('.reuse-summary')) == sum(bool(item['facts']) for item in exp.values())
            for item, state in exp.items():
                node = new.select_one('#q-how-data li[data-item-id="' + item + '"]'); assert node
                original = old.select_one('#q-how-data li[data-item-id="' + item + '"]'); assert original
                assert [probe.dom(n) for n in node.select(':scope > h5, :scope > strong')] == [probe.dom(n) for n in original.select(':scope > h5, :scope > strong')]
                assert [(n['data-fact-id'], n.get_text()) for n in node.select(':scope > .reuse-summary > span')] == state['facts']
                details = node.select(':scope > [data-fact-id="reuse-conditions-detail"]')
                assert len(details) == bool(state['detail'] and (state['filled'] or profile == 'review'))
                if details:
                    if state['filled']:
                        detail = copy.deepcopy(details[0]); detail.p.decompose()
                        wanted = BeautifulSoup('<div class="answer-detail" data-fact-id="reuse-conditions-detail" data-status="complete">' + oracle[case][state['detail']] + '</div>', 'html.parser').div
                        assert probe.dom(detail) == probe.dom(wanted), 'Original Markdown changed'
                        if filename == 'document.html':
                            authored_fragments.update(compact(n.get_text()) for n in wanted.select('p, li, tr') if n.get_text().strip())
                    else: assert details[0]['data-status'] == 'missing'
                if filename == 'document.html':
                    all_facts.extend(text for _, text in state['facts'])
                    summary_counts.append(dict(facts=len(state['facts']), paragraphs=len(node.select(':scope > .reuse-summary'))))
            for part in new.select('.reuse-summary, [data-fact-id="reuse-conditions-detail"]'):
                parser = probe.BlockProbe(); parser.feed(str(part))
                assert not parser.errors and not parser.stack, 'Invalid owned block nesting'
            if profile == 'submission':
                assert not [n for n in new.select('.data-gap') if not n.find_parent(class_='answer-detail')], 'Owned prompt leaked'
            if case in ['P21', 'EMPTY']: assert (a / filename).read_bytes() == (b / filename).read_bytes(), 'Unaffected control HTML changed'
        page_counts = {}
        for label, filename in [('pdf', 'document.pdf'), ('word_preview', 'word-preview/document.pdf')]:
            before, bp, _ = layout(a / filename); after, ap, text = layout(b / filename)
            for fact in all_facts: assert compact(fact) in text, 'Native document lost a selected fact'
            for fragment, count in authored_fragments.items():
                assert text.count(fragment) >= count, 'Native document lost authored text or table rows'
            if case in ['P21', 'EMPTY']:
                assert etree.tostring(before.find('.//{*}body')) == etree.tostring(after.find('.//{*}body'))
                for number in range(1, len(ap) + 1):
                    raster = lambda file: subprocess.check_output(['pdftoppm', '-f', str(number), '-l', str(number), '-singlefile', '-r', '72', '-png', str(file)])
                    assert raster(a / filename) == raster(b / filename), 'Unaffected control page changed'
            page_counts[label] = dict(baseline=len(bp), candidate=len(ap))
        with zipfile.ZipFile(b / 'document.docx') as archive:
            xml = etree.fromstring(archive.read('word/document.xml'))
            question = word_question(xml)
            texts = compact(''.join(question.xpath('.//*[local-name()="t"]/text()')))
            for fact in all_facts: assert compact(fact) in texts, 'Editable Word lost a selected fact'
            for fragment, count in authored_fragments.items():
                assert texts.count(fragment) >= count, 'Editable Word lost authored text or table rows'
            if case in ['SYN-OTHER', 'SYN-LONG']:
                tables = question.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl')
                actual_tables = sum('Preserve this authored table.' in ''.join(t.xpath('.//*[local-name()="t"]/text()')) for t in tables)
                assert actual_tables == (8 if case == 'SYN-LONG' else 1), 'Authored editable Word tables lost'
        rows.append(dict(case=case, locale=locale, profile=profile, passed=True,
            fact_count=len(all_facts), summaries=summary_counts, pages=page_counts,
            untouched_q2_to_q15=True, original_restrictions_markdown_verified=True,
            unchanged_control=case in ['P21', 'EMPTY']))
        print(json.dumps(rows[-1]), flush=True)
    assert len(rows) == 28
    result = dict(passed=True, prototype_only=True, release_acceptance=False, rows=rows,
        prior_files_unchanged=len(inventory), native_dsw_server=False, native_ms_word=False,
        worker_image='sha256:6d3cbcab3294e760a4d92e27bec72d4fb23a0adb2cc1734d981478688741ab11',
        word_preview_image=subprocess.check_output(['docker', 'image', 'inspect', 'gotenberg/gotenberg:8', '--format', '{{.Id}}'], text=True).strip(),
        new_native_combinations=44, reused_baseline_combinations=12,
        remote_writes=0, credentials_used=False)
    with (ROOT / 'checks-v2.json').open('x') as stream: stream.write(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__': main()
