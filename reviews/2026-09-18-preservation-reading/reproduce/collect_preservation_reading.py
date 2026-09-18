"""Freeze checked native bilingual Q11 outputs without duplicating embedded fonts."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from bs4 import BeautifulSoup
from artifact_utils import sha
from collect_profile_pagination import contact

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'prior-controls', 'prior-profile', 'candidate', 'english', 'report', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--failed-run', type=Path, required=True)
    p.add_argument('--failed-checks', type=Path, nargs='*', default=[])
    a = p.parse_args(); assert not a.output.exists()
    report = json.loads(a.report.read_text())
    assert report['selected_checks_passed'] and len(report['rows']) == 12
    assert not report['release_acceptance'] and not report['microsoft_word_acceptance']
    assert report['checker_sha256'] == sha(ROOT/'scripts/check_preservation_reading_outputs.py')
    assert report['contract_sha256'] == sha(a.english/'scripts/preservation_reading_contract.py')
    a.output.mkdir(parents=True)
    def keep(source, name):
        destination = a.output/name; destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    keep(a.report, 'provenance/native-comparison.json')
    for name in ('manifest.json', 'missing-info-render-report.json', 'render-profile-partial-review-english-html.log'):
        keep(a.failed_run/name, 'diagnostics-quota/'+name)
    for source in a.failed_checks: keep(source, 'diagnostics-checker/'+source.name)
    for name in ('manifest.json', 'preservation-reading-scope.json', 'preservation-reading-engine-en.json',
                 'preservation-reading-engine-zh.json', 'structure-audit.json', 'translation-audit.json'):
        keep(a.candidate/name, 'provenance/candidate-'+name)
    for key, folder in (('before-controls', a.prior_controls), ('before-profile', a.prior_profile), ('after', a.build)):
        for name in ('manifest.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json'):
            keep(folder/name, 'provenance/'+key+'-'+name)
        for path in folder.glob('word-preview-*.json'): keep(path, 'provenance/'+key+'-'+path.name)
    for name in (*report['helper_sha256'], 'check_preservation_reading_outputs.py', 'collect_preservation_reading.py'):
        keep(ROOT/'scripts'/name, 'reproduce/'+name)
    keep(a.english/'scripts/preservation_reading_contract.py', 'reproduce/preservation_reading_contract.py')
    keep(ROOT/'pipeline.yml', 'reproduce/pipeline.yml')
    inventory = dict(version='0.3.39', native_export=True, release_acceptance=False,
        microsoft_word_acceptance=False, collector_sha256=sha(Path(__file__)), rows=[])
    for row in report['rows']:
        stem = row['case']+'-'+row['profile']+'-'+row['language']
        prior = a.prior_profile if row['case'] == 'profile-partial' else a.prior_controls
        for phase, folder, key in (('before', prior, 'prior_artifact_sha256'), ('after', a.build, 'artifact_sha256')):
            for name, digest in row[key].items():
                source = folder/name; assert sha(source) == digest, source
                if name.endswith('.html'):
                    soup = BeautifulSoup(source.read_text(), 'html.parser')
                    questions = soup.select('.question'); assert len(questions) == 15
                    target = a.output/phase/'question-content'/source.name; target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text('<!-- Native HTML SHA256: '+digest+' -->\n'+ '\n'.join(str(q) for q in questions)+'\n')
                else:
                    relative = name.replace('renders/', 'native/', 1)
                    keep(source, phase+'/'+relative)
            inventory['rows'].append(dict(phase=phase, stem=stem, word_pages=row['word_pages'], pdf_pages=row['pdf_pages']))
        if row['case'] == 'profile-partial':
            contact(a.build/'word-preview'/(stem+'.pdf'), a.output/'visual'/(stem+'-word.png'), stem)
    for phase in ('before', 'after'):
        pdf = a.output/phase/'word-preview/profile-partial-submission-chinese.pdf'
        for page in (4, 5):
            subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-scale-to', '1600', '-singlefile', '-png',
                str(pdf), str(a.output/'visual'/(phase+'-chinese-submission-p'+str(page)))], check=True, capture_output=True)
    (a.output/'inventory.json').write_text(json.dumps(inventory, indent=2)+'\n')
    print(json.dumps(dict(pairs=12, archived_native_pdf_docx=48, archived_word_previews=24)))


if __name__ == '__main__': main()
