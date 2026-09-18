"""Freeze the bounded dual-profile native pilot without embedding fonts four times."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw
from artifact_utils import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'candidate', 'report', 'english', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    proof = json.loads(a.report.read_text()); assert proof['selected_checks_passed'] and not proof['release_acceptance']
    assert proof['package_sha256'] == {n: sha(a.build/n) for n in ('english.zip', 'chinese.zip')}
    a.output.mkdir(parents=True)
    def copy(source, relative):
        dest = a.output/relative; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, dest)
    for name in ('manifest.json', 'missing-info-render-report.json', 'worker-start.json', 'worker-lifecycle.json',
                 'runtime-restoration.json', 'owned-test-template-cleanup.json'):
        copy(a.build/name, 'provenance/'+name)
    copy(a.candidate/'manifest.json', 'provenance/candidate-manifest.json')
    copy(a.candidate/'output-profiles-scope.json', 'provenance/output-profiles-scope.json')
    copy(a.report, 'output-profiles-report.json')
    copy(a.english/'requirements/output-profiles.json', 'provenance/profile-contract.json')
    for path in a.build.glob('word-preview-*.json'): copy(path, 'provenance/'+path.name)
    rows = []
    for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
        copy(a.build/('internal-checklist-'+language+'.json'), 'internal-checklist-'+language+'.json')
        notes = json.loads((a.build/('internal-checklist-'+language+'.json')).read_text())
        text = '# Internal checklist / 內部檢核清單\n\n局部實驗；不是全問卷完整率或核准繳交證明。\n\n'
        for item in notes['items']:
            text += '- '+item['question']+' / `'+item['fact']+'` ('+item['status']+'): '+item['text']+'\n'
        (a.output/('internal-checklist-'+language+'.md')).write_text(text)
        for suffix in ('.json', '.events.json'):
            f = a.english/'fixtures/pilot'/locale/('profile-partial'+suffix)
            copy(f, 'fixtures/'+locale+'/'+f.name)
        for profile in ('review', 'submission'):
            stem = 'profile-partial-'+profile+'-'+language
            raw = a.build/'renders'/(stem+'.html'); soup = BeautifulSoup(raw.read_text(), 'html.parser')
            target = a.output/'question-content'/(stem+'.html'); target.parent.mkdir(exist_ok=True)
            target.write_text('<!-- Native HTML SHA256: '+sha(raw)+' -->\n'+str(soup.select_one('#dmp-projects'))+'\n'+str(soup.select_one('#dmp-content'))+'\n')
            for ext in ('html', 'pdf', 'docx'):
                source = a.build/'renders'/(stem+'.'+ext)
                copy(source.with_name(source.name+'.fixture.json'), 'native/'+source.name+'.fixture.json')
                if ext != 'html': copy(source, 'native/'+source.name)
            preview = a.build/'word-preview'/(stem+'.pdf'); copy(preview, 'word-preview/'+preview.name)
            for fmt, pdf in [('pdf', a.build/'renders'/(stem+'.pdf')), ('word-preview', preview)]:
                page_text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
                textfile = a.output/'page-text'/(stem+'-'+fmt+'.txt'); textfile.parent.mkdir(exist_ok=True); textfile.write_text(page_text)
                with tempfile.TemporaryDirectory(prefix='output-profiles-contact-') as tmp:
                    subprocess.run(['pdftoppm', '-scale-to', '840', '-png', str(pdf), str(Path(tmp)/'page')], check=True, capture_output=True)
                    pages = sorted(Path(tmp).glob('page-*.png'), key=lambda f: int(f.stem.split('-')[-1]))
                    sheet = Image.new('RGB', (1860, ((len(pages)+2)//3)*880), '#ddd'); draw = ImageDraw.Draw(sheet)
                    for i, f in enumerate(pages):
                        with Image.open(f) as page: sheet.paste(page.convert('RGB'), ((i%3)*620+12, (i//3)*880+27))
                        draw.text(((i%3)*620+12, (i//3)*880+8), f'{profile} {language} {fmt} p{i+1}', fill='black')
                    target = a.output/'visual'/(stem+'-'+fmt+'.png'); target.parent.mkdir(exist_ok=True); sheet.save(target)
                rows.append(dict(language=language, profile=profile, format=fmt, pages=len(pages), sha256=sha(pdf)))
    for name in ('check_output_profiles.py', 'collect_output_profiles_review.py'):
        copy(Path(__file__).parent/name, 'reproduce/'+name)
    (a.output/'inventory.json').write_text(json.dumps(dict(version='0.3.38', release_acceptance=False,
        microsoft_word_acceptance=False, native_renders=12, word_previews=4, pages=sum(r['pages'] for r in rows),
        rows=rows), indent=2)+'\n')
    print(json.dumps(dict(native_renders=12, word_previews=4, pages=sum(r['pages'] for r in rows))))


if __name__ == '__main__': main()
