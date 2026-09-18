"""Freeze standalone pagination rehearsals; never promote them to native exports."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

from lxml import etree as E
from PIL import Image, ImageDraw
from artifact_utils import sha
from rehearse_profile_pagination import validate_change

ROOT = Path(__file__).resolve().parents[1]


def contact(pdf, target, title):
    with tempfile.TemporaryDirectory(prefix='profile-pagination-contact-') as temp:
        subprocess.run(['pdftoppm', '-scale-to', '840', '-png', str(pdf), str(Path(temp)/'page')], check=True, capture_output=True)
        pages = sorted(Path(temp).glob('page-*.png'), key=lambda p: int(p.stem.split('-')[-1]))
        sheet = Image.new('RGB', (1860, ((len(pages)+2)//3)*880), '#ddd')
        draw = ImageDraw.Draw(sheet)
        for i, path in enumerate(pages):
            with Image.open(path) as page: sheet.paste(page.convert('RGB'), ((i%3)*620+12, (i//3)*880+27))
            draw.text(((i%3)*620+12, (i//3)*880+8), title+' p'+str(i+1), fill='black')
        target.parent.mkdir(parents=True, exist_ok=True); sheet.save(target)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('word', 'pdf', 'output'): p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--native', type=Path, default=ROOT/'reviews/2026-09-18-output-profiles')
    p.add_argument('--diagnostic-reports', type=Path, nargs='*', default=[])
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=False)
    inventory = dict(template_modified=False, release_acceptance=False, microsoft_word_acceptance=False,
        prior_native_archive=str(a.native.relative_to(ROOT)), rows=[],
        source_template_version='0.3.38', collector_sha256=sha(Path(__file__)))
    def keep(source, relative):
        target = a.output/relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
    for kind, folder, runner in [('word', a.word, 'rehearse_profile_pagination.py'), ('pdf', a.pdf, 'rehearse_profile_pdf.py')]:
        report = json.loads((folder/'report.json').read_text())
        assert report['completed'] and not report['release_acceptance'] and not report['native_export']
        assert len(report['rows']) == 8 and report['checker_sha256'] == sha(ROOT/'scripts'/runner)
        keep(folder/'report.json', kind+'/report.json'); keep(ROOT/'scripts'/runner, 'reproduce/'+runner)
        for row in report['rows']:
            stem = 'profile-partial-'+row['mode']+'-'+row['language']
            trial = stem+'-'+row['trial']; pdf = folder/(trial+'.pdf')
            assert sha(pdf) == row['pdf_sha256']; keep(pdf, kind+'/'+pdf.name)
            if kind == 'word':
                docx = folder/(trial+'.docx'); original = a.native/'native'/(stem+'.docx')
                assert sha(docx) == row['docx_sha256'] and sha(original) == row['source_sha256']
                with zipfile.ZipFile(original) as before, zipfile.ZipFile(docx) as after:
                    assert set(before.namelist()) == set(after.namelist())
                    for name in before.namelist():
                        if name not in ('word/document.xml', 'word/styles.xml'): assert before.read(name) == after.read(name)
                    validate_change(*[E.fromstring(z.read(n)) for z in (before, after) for n in ('word/document.xml', 'word/styles.xml')], row['trial'])
                keep(docx, kind+'/'+docx.name)
            else:
                assert sha(a.native/'native'/(stem+'.pdf')) == row['source_pdf_sha256']
                native_html = a.native/'question-content'/(stem+'.html')
                assert native_html.read_text().splitlines()[0] == '<!-- Native HTML SHA256: '+row['source_html_sha256']+' -->'
            text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
            target = a.output/'page-text'/(kind+'-'+trial+'.txt'); target.parent.mkdir(exist_ok=True); target.write_text(text)
            if row['trial'] != 'baseline':
                contact(pdf, a.output/'visual'/(kind+'-'+trial+'.png'), kind+' '+row['mode']+' '+row['language'])
            inventory['rows'].append(dict(kind=kind, stem=trial, pages=row['pages'], sha256=sha(pdf)))
    for path in a.diagnostic_reports:
        keep(path, 'diagnostics/'+path.parent.name+'.json')
    for name in ('pipeline.yml',): keep(ROOT/name, 'reproduce/'+name)
    keep(Path(__file__), 'reproduce/'+Path(__file__).name)
    # Preserve the measured font discrepancy separately from the successful A/B.
    font_cases = [a.native/'native/profile-partial-review-chinese.pdf',
                  a.pdf/'profile-partial-review-chinese-baseline.pdf',
                  a.pdf/'profile-partial-review-chinese-keep-short-q15.pdf']
    fonts = {('native' if i == 0 else 'baseline' if i == 1 else 'keep-short-q15'):
        dict(sha256=sha(path), pdffonts=subprocess.check_output(['pdffonts', str(path)], text=True)) for i, path in enumerate(font_cases)}
    (a.output/'font-baseline-discrepancy.json').write_text(json.dumps(fonts, indent=2)+'\n')
    for kind, stem, page in [('word', 'profile-partial-submission-chinese-joined-label', 5),
                             ('pdf', 'profile-partial-submission-chinese-keep-short-q15', 6)]:
        subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-scale-to', '1600', '-singlefile', '-png',
            str(a.output/kind/(stem+'.pdf')), str(a.output/'visual'/(kind+'-chinese-submission-p'+str(page)))], check=True, capture_output=True)
    inventory['trial_pdfs'] = len(inventory['rows'])
    inventory['trial_pages'] = sum(r['pages'] for r in inventory['rows'])
    (a.output/'inventory.json').write_text(json.dumps(inventory, indent=2)+'\n')
    print(json.dumps(dict(trial_pdfs=inventory['trial_pdfs'], pages=inventory['trial_pages'], release_acceptance=False)))


if __name__ == '__main__': main()
