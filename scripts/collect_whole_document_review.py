"""Freeze a three-case reading audit; this is an inventory, not an acceptance test."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from bs4 import BeautifulSoup
from docx import Document
from PIL import Image, ImageDraw

from artifact_utils import sha
from check_word_short_budget_outputs import verify_preview_paragraphs


CASES = ('metadata-complete', 'metadata-partial', 'narrative-long')
LANGUAGES = {'english': 'en', 'chinese': 'zh-Hant'}


def compact(text):
    return ''.join(text.split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('baseline', 'fresh', 'english', 'output'):
        parser.add_argument('--' + key, required=True, type=Path)
    args = parser.parse_args()
    assert not args.output.exists(), 'Do not overwrite earlier evidence'
    args.output.mkdir(parents=True)

    def copy(source, target):
        destination = args.output / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    inventory = json.loads((args.fresh / 'question-inventory.json').read_text())
    requirements = json.loads((args.english / 'requirements/science-europe-2021.json').read_text())
    requirement_ids = {r['number']: r['id'] for r in requirements['requirements']}
    rows = []
    for label, root in [('reused', args.baseline), ('fresh', args.fresh)]:
        render = json.loads((root / 'missing-info-render-report.json').read_text())
        assert render['all_renders_succeeded']
        assert len(render['renders']) == (30 if label == 'reused' else 6)
        for name in ('english.zip', 'chinese.zip'):
            assert sha(root / name) == sha(args.baseline / name)
        for name in ('manifest.json', 'missing-info-render-report.json', 'worker-start.json',
                     'worker-lifecycle.json', 'runtime-restoration.json', 'owned-test-template-cleanup.json'):
            copy(root / name, 'provenance/' + label + '/' + name)
        for path in root.glob('word-preview-*.json'):
            copy(path, 'provenance/' + label + '/' + path.name)

    for case in CASES:
        root = args.fresh if case == 'narrative-long' else args.baseline
        preview_rows = [row for path in root.glob('word-preview-*.json')
                        for row in json.loads(path.read_text())['rows']]
        for language, locale in LANGUAGES.items():
            stem = case + '-' + language
            source_html = root / 'renders' / (stem + '.html')
            soup = BeautifulSoup(source_html.read_text(), 'html.parser')
            content = soup.select_one('#dmp-content')
            questions = content.select('.question')
            assert len(questions) == 15 and len(content.select('.dmp-section')) == 6
            html_target = args.output / 'question-content' / (stem + '.html')
            html_target.parent.mkdir(exist_ok=True)
            html_target.write_text('<!-- Extracted from native HTML SHA256: ' + sha(source_html) + ' -->\n' + str(content) + '\n')
            recipe = args.english / 'fixtures/pilot' / locale / (case + '.json')
            events = recipe.with_name(case + '.events.json')
            for source in (recipe, events):
                copy(source, 'fixtures/' + locale + '/' + source.name)
            for extension in ('html', 'pdf', 'docx'):
                source = root / 'renders' / (stem + '.' + extension)
                receipt = json.loads(source.with_name(source.name + '.fixture.json').read_text())
                assert receipt['recipe_sha256'] == sha(recipe) and receipt['events_sha256'] == sha(events)
                assert receipt['km_sha256'] == inventory['knowledge_models'][locale]['km_sha256']
                assert receipt['package_sha256'] == sha(root / (language + '.zip'))
                copy(source.with_name(source.name + '.fixture.json'), 'native/' + source.name + '.fixture.json')
                if extension != 'html':
                    copy(source, 'native/' + source.name)
            docx = root / 'renders' / (stem + '.docx')
            preview = root / 'word-preview' / (stem + '.pdf')
            receipts = [r for r in preview_rows if r['name'] == stem]
            assert len(receipts) == 1
            assert receipts[0]['docx_sha256'] == sha(docx) and receipts[0]['preview_sha256'] == sha(preview)
            preview_paragraphs = verify_preview_paragraphs(Document(docx), preview, soup)
            copy(preview, 'word-preview/' + preview.name)
            row = {'case': case, 'language': language,
                   'render_origin': 'fresh' if case == 'narrative-long' else 'reused-exact-0.3.37',
                   'html_sha256': sha(source_html), 'docx_sha256': sha(docx),
                   'verified_word_preview_paragraphs': preview_paragraphs,
                   'questions': [], 'formats': {}}
            for number, question in enumerate(questions, 1):
                assert question.h3.get_text(strip=True).startswith(str(number) + '.')
                row['questions'].append({'id': question['id'], 'requirement_id': requirement_ids[number],
                    'html_requirement_attribute': question.get('data-requirement-id'),
                    'heading': question.h3.get_text(' ', strip=True),
                    'answer': question.select_one('.answer').get_text(' ', strip=True),
                    'flags': [{'text': n.get_text(' ', strip=True), 'status': n.get('data-status'),
                               'fact_id': n.get('data-fact-id')} for n in question.select('.data-gap, .data-review, .data-unmapped')]})
            for fmt, pdf in [('pdf', root / 'renders' / (stem + '.pdf')), ('word-preview', preview)]:
                text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
                pages = text.split('\f')
                assert not pages[-1].strip()
                pages.pop()
                target = args.output / 'page-text' / (stem + '-' + fmt + '.txt')
                target.parent.mkdir(exist_ok=True)
                target.write_text(text)
                locations = {}
                for question in row['questions']:
                    matches = [i for i, page in enumerate(pages, 1) if compact(question['heading']) in compact(page)]
                    assert len(matches) == 1, (stem, fmt, question['id'], matches)
                    locations[question['id']] = matches[0]
                markers = re.findall(r'\[(\d{2})\]', text)
                if case == 'narrative-long':
                    assert markers == [f'{i:02d}' for i in range(1, 81)], (stem, fmt, markers)
                row['formats'][fmt] = {'sha256': sha(pdf), 'pages': len(pages),
                    'question_heading_pages': locations,
                    'numbered_stress_paragraphs': len(markers) if case == 'narrative-long' else None}
                # Overview only: precise findings require the original PDF or a larger crop.
                with tempfile.TemporaryDirectory(prefix='whole-dmp-contact-') as temporary:
                    prefix = Path(temporary) / 'page'
                    subprocess.run(['pdftoppm', '-scale-to', '840', '-png', str(pdf), str(prefix)], check=True, capture_output=True)
                    images = sorted(Path(temporary).glob('page-*.png'), key=lambda p: int(p.stem.split('-')[-1]))
                    assert len(images) == len(pages)
                    for start in range(0, len(images), 6):
                        group = images[start:start + 6]
                        sheet = Image.new('RGB', (1240, ((len(group) + 1) // 2) * 880), '#dddddd')
                        draw = ImageDraw.Draw(sheet)
                        for i, path in enumerate(group):
                            with Image.open(path) as page:
                                sheet.paste(page.convert('RGB'), ((i % 2) * 620 + 12, (i // 2) * 880 + 27))
                            draw.text(((i % 2) * 620 + 12, (i // 2) * 880 + 8), f'{stem} {fmt} p{start + i + 1}', fill='black')
                        visual = args.output / 'visual' / f'{stem}-{fmt}-p{start + 1}-{start + len(group)}.png'
                        visual.parent.mkdir(exist_ok=True)
                        sheet.save(visual)
            events_by_path = {event['path']: event['value'] for event in json.loads(events.read_text()) if event['type'] == 'SetReplyEvent'}
            selected = []
            for question in inventory['knowledge_models'][locale]['questions']:
                if set(question['bindings']) & {'ownershipQUuid', 'sharedWorkspaceQUuid', 'sharedAccessControlQUuid',
                                                'risksQUuid', 'risksInfoLossQUuid', 'risksInfoLeakQUuid', 'risksInfoVandalismQUuid'}:
                    path = '.'.join(question['path'])
                    selected.append({**question, 'fixture_reply': events_by_path.get(path)})
            row['selected_input_questions'] = selected
            rows.append(row)
    report = {'scope': 'Whole-document reading inventory of three synthetic bilingual cases',
        'version': '0.3.37', 'release_acceptance': False, 'microsoft_word_acceptance': False,
        'fresh_native_renders': 6, 'reused_native_renders': 12, 'word_previews': 6,
        'collector_sha256': sha(Path(__file__)),
        'package_sha256': {name: sha(args.fresh / name) for name in ('english.zip', 'chinese.zip')},
        'source_commit': inventory['source_commit'],
        'limits': ['metadata-complete means only its metadata follow-ups, NOT a complete DMP',
                   'narrative-long repeats 80 paragraphs intentionally in the source answer',
                   '15 headings and 6 sections do not establish Science Europe compliance',
                   'Word preview is LibreOffice, not Microsoft Word',
                   'Tables-only isolated worker, not deployment-worker acceptance'], 'rows': rows}
    (args.output / 'inventory.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    copy(args.fresh / 'question-inventory.json', 'provenance/question-inventory.json')
    copy(args.english / 'requirements/science-europe-2021.json', 'provenance/pinned-requirements.json')
    for name in ('06-access-security.html.j2', '08-copyright-ipr.html.j2'):
        copy(args.english / 'src/questions' / name, 'source/' + name)
    copy(Path(__file__), 'reproduce/' + Path(__file__).name)
    print(json.dumps({'documents': len(rows), 'pages': sum(f['pages'] for r in rows for f in r['formats'].values()),
                      'release_acceptance': False}))


if __name__ == '__main__':
    main()
