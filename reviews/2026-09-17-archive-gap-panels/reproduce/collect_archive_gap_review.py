"""Freeze 0.3.30 bilingual native evidence without publishing full embedded-font HTML."""
import argparse
import json
from pathlib import Path
import shutil
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_archive_gap_outputs import CASES, EXTRA

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['build', 'prior', 'prior-extra', 'candidate', 'rebuild', 'english', 'readme', 'output']:
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    report = json.loads((a.build/'archive-gap-report.json').read_text())
    assert report['selected_checks_passed'] and len(report['rows']) == 16
    assert {(r['case'], r['language']) for r in report['rows']} == {(c, l) for c in CASES for l in ['english', 'chinese']}
    assert all(r['passed'] and not r['errors'] and not r['reading_issues'] for r in report['rows'])
    assert sha(ROOT/'scripts/check_archive_gap_outputs.py') == report['checker_sha256']
    assert sha(a.english/'scripts/probe_archive_gap_panels.py') == report['selector_sha256']
    for name, digest in report['helper_sha256'].items(): assert sha(ROOT/'scripts'/name) == digest
    for name, digest in report['package_sha256'].items(): assert sha(a.build/name) == sha(a.candidate/name) == sha(a.rebuild/name) == digest
    for root, count in [(a.build, 48), (a.prior_extra, 18)]:
        renders = json.loads((root/'missing-info-render-report.json').read_text())
        assert renders['all_renders_succeeded'] and len(renders['renders']) == count
        assert all(r['rendered'] for r in renders['renders'])
        cleanup = json.loads((root/'owned-test-template-cleanup.json').read_text())
        assert len(cleanup['deleted']) == 2 and cleanup['project_references'] == cleanup['document_references'] == 0
        for backup in cleanup['backups'].values(): assert sha(Path(backup['path'])) == backup['sha256']
    assert json.loads((a.build/'runtime-restoration.json').read_text())['restored_stock_and_stopped']
    assert json.loads((a.candidate/'archive-gap-scope.json').read_text())['passed']
    identifier = json.loads((a.candidate/'identifier-spacing-engine.json').read_text())
    assert identifier['passed'] and len(identifier['word']) == 13
    for language in ['english', 'chinese']:
        engine = json.loads((a.candidate/('archive-gap-engine-'+language+'.json')).read_text())
        assert engine['passed'] and len(engine['rows']) == 40
    for row in report['rows']:
        prior = a.prior_extra if row['case'] in EXTRA else a.prior
        for name, digest in row['artifact_sha256'].items(): assert sha(a.build/name) == digest
        for name, digest in row['prior_artifact_sha256'].items(): assert sha(prior/name) == digest

    def copy(source, name):
        target = a.output/name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)

    def artifact(root, prefix, stem):
        for fmt in ['pdf', 'docx']: copy(root/'renders'/(stem+'.'+fmt), prefix+'/native/'+stem+'.'+fmt)
        for fmt in ['html', 'pdf', 'docx']: copy(root/'renders'/(stem+'.'+fmt+'.fixture.json'), prefix+'/native/'+stem+'.'+fmt+'.fixture.json')
        copy(root/'word-preview'/(stem+'.pdf'), prefix+'/word-preview/'+stem+'.pdf')
        html = root/'renders'/(stem+'.html'); soup = BeautifulSoup(html.read_text(), 'html.parser')
        target = a.output/prefix/'question-content'/(stem+'.html'); target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('<!-- Native HTML SHA256: '+sha(html)+' -->\n'+str(soup.select_one('#dmp-content'))+'\n')

    for row in report['rows']:
        stem = row['case']+'-'+row['language']; artifact(a.build, 'after', stem)
        if row['case'] in EXTRA: artifact(a.prior_extra, 'before-extra', stem)
        locale = 'en' if row['language'] == 'english' else 'zh-Hant'
        for suffix in ['.json', '.events.json']: copy(a.english/'fixtures/pilot'/locale/(row['case']+suffix), 'fixtures/'+locale+'/'+row['case']+suffix)
    for name in ['manifest.json', 'archive-gap-report.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json',
                 'worker-start.json', 'worker-lifecycle.json', 'runtime-restoration.json']:
        copy(a.build/name, 'after/'+name)
    for name in ['manifest.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json']:
        copy(a.prior_extra/name, 'before-extra/'+name)
    for label, root in [('candidate', a.candidate), ('rebuild', a.rebuild)]: copy(root/'manifest.json', label+'-manifest.json')
    for name in ['archive-gap-scope.json', 'archive-gap-engine-english.json', 'archive-gap-engine-chinese.json', 'identifier-spacing-engine.json']:
        copy(a.candidate/name, 'probes/'+name)
    for folder in ['diagnostics', 'visual']:
        for f in sorted((a.build/folder).iterdir()):
            if f.is_file(): copy(f, folder+'/'+f.name)
    for name in sorted(set(report['helper_sha256']) | {'check_archive_gap_outputs.py', 'collect_archive_gap_review.py', 'probe_archive_gap_scope.py'}):
        copy(ROOT/'scripts'/name, 'reproduce/'+name)
    for name in ['probe_archive_gap_panels.py', 'generate_archive_gap_fixtures.py', 'probe_identifier_spacing.py']: copy(a.english/'scripts'/name, 'reproduce/'+name)
    copy(ROOT/'pipeline.yml', 'reproduce/pipeline.yml')
    for language in ['en', 'translated']:
        for name in ['layout.css', 'post-project-archive.html.j2']: copy(a.candidate/language/'src'/name, 'source/'+language+'/'+name)
    copy(a.readme, 'README.md')
    checks = {str(f.relative_to(a.output)): sha(f) for f in sorted(a.output.rglob('*')) if f.is_file()}
    (a.output/'checksums.json').write_text(json.dumps(checks, indent=2)+'\n')
    print(json.dumps({'archived': str(a.output), 'native_outputs': 48, 'word_previews': 16, 'extra_baseline_outputs': 18, 'files': len(checks)}))


if __name__ == '__main__': main()
