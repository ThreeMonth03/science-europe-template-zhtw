"""Public synthetic WeasyPrint regression for Q10's type/value page split.

Run inside the pinned worker image, with --network none. No questionnaire data,
live DSW, or real identifier is used. This tests CSS, not full Word pagination.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile
from jinja2 import Environment
from weasyprint import HTML


def styles(path):
    with zipfile.ZipFile(path) as archive:
        files = {f['fileName']: f['content'] for f in json.loads(archive.read('template/template.json'))['files']}
        def assets(name):
            return SimpleNamespace(data_base64=base64.b64encode(archive.read('template/assets/' + name)).decode())
        css = '\n'.join(files['src/' + name] for name in ['style.css', 'layout.css'])
        return Environment().from_string(css).render(assets=assets,
            ctx={'document': {'formatUuid': '9fd0a115-4b8b-5013-a084-eaf2890ec940'}})


def render(css, height, locale, owned=True):
    # A realistic single short identifier near the page boundary. Text precedes
    # strong but does NOT prevent strong matching CSS :first-child.
    identifier = 'ark:/12345/public-synthetic-control'
    prefix = '<div class="answer-detail">' if not owned else ''
    suffix = '</div>' if not owned else ''
    source = ('<!DOCTYPE html><html lang="' + locale + '"><head><meta charset="utf-8"><style>' + css +
        '</style></head><body><div style="height:' + str(height) + 'px"></div>'
        '<div id="q-share-restrictions" class="question"><div class="answer"><div class="dataset-section">'
        + prefix + '<ul><li>ARK: <strong>' + identifier + '</strong></li></ul>' + suffix + '</div></div></div></body></html>')
    document = HTML(string=source).render()
    positions = []
    for page_index, page in enumerate(document.pages, 1):
        for box in page._page_box.descendants():
            if type(box).__name__ == 'TextBox' and (box.text.strip() == 'ARK:' or identifier in box.text):
                positions.append(dict(text=box.text.strip(), page=page_index, x=box.position_x, y=box.position_y,
                                      width=box.width, height=box.height))
    assert len(positions) == 2, positions
    return document, positions


def run(baseline, prototype, output):
    assert not output.exists(); output.mkdir(parents=True)
    rows = []
    for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
        css = [styles(root / (language + '.zip')) for root in [baseline, prototype]]
        selected = None
        for height in [910, 900, 920, 890, 930, 880, 940]:
            before, old = render(css[0], height, locale)
            after, new = render(css[1], height, locale)
            if old[0]['page'] != old[1]['page'] and new[0]['page'] == new[1]['page']:
                assert abs(new[0]['y'] - new[1]['y']) < 3
                selected = height
                for phase, doc in [('before', before), ('after', after)]:
                    doc.write_pdf(output / (language + '-boundary-' + phase + '.pdf'))
                rows.append(dict(language=language, case='short-identifier-boundary', height=height, before=old, after=new, passed=True))
                break
        assert selected is not None, 'The fixture must reproduce and fix a real page split'
        before, old = render(css[0], 0, locale, owned=False)
        after, new = render(css[1], 0, locale, owned=False)
        assert old == new, 'An authored list must not match the owned identifier rule'
        for phase, doc in [('before', before), ('after', after)]:
            doc.write_pdf(output / (language + '-authored-' + phase + '.pdf'))
        rows.append(dict(language=language, case='authored-list-control', before=old, after=new, passed=True))
    result = dict(passed=True, synthetic_only=True, output_profile='submission', native_word=False, release_acceptance=False,
        renderer='WeasyPrint in DSW 4.30.2 worker', checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        packages={phase: {language: hashlib.sha256((root / (language + '.zip')).read_bytes()).hexdigest()
            for language in ['english', 'chinese']} for phase, root in [('before', baseline), ('after', prototype)]}, rows=rows)
    (output / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=True, checks=len(rows), pdfs=len(list(output.glob('*.pdf'))))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['baseline', 'prototype', 'output']: parser.add_argument('--' + key, type=Path, required=True)
    a = parser.parse_args(); run(a.baseline, a.prototype, a.output)
