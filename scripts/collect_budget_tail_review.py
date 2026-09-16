"""Archive rejected pagination trials without changing a template or a source export."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from lxml import etree as E

from artifact_utils import sha
from rehearse_budget_tail import CASES, PROFILES, validate_change

ROOT = Path(__file__).resolve().parents[1]


def geometry(pdf):
    raw = subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-'])
    return [E.tostring(page, method='c14n') for page in E.fromstring(raw).findall('.//{*}page')]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['prior', 'trials', 'earlier-trials', 'failed-trials', 'destination']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    report = json.loads((a.trials / 'report.json').read_text())
    assert report['completed'] and not report['native_export'] and not report['release_acceptance']
    assert report['checker_sha256'] == sha(ROOT / 'scripts/rehearse_budget_tail.py')
    expected = {(case, lang, profile) for case in CASES for lang in ['english', 'chinese'] for profile in PROFILES}
    assert len(report['rows']) == len(expected) == 24
    assert {(r['case'], r['language'], r['profile']) for r in report['rows']} == expected
    copies = []
    def keep(path, relative):
        assert path.is_file()
        copies.append((path, Path(relative)))
    for name, value in report['prior_package_sha256'].items():
        assert sha(a.prior / name) == value
    baseline_geometry = []
    for row in report['rows']:
        stem = row['case'] + '-' + row['language']
        source = a.prior / 'renders' / (stem + '.docx')
        assert sha(source) == row['source_sha256']
        assert sha(source.with_suffix('.html')) == row['source_html_sha256']
        trial = a.trials / (stem + '-' + row['profile'] + '.docx')
        assert sha(trial) == row['docx_sha256'] and sha(trial.with_suffix('.pdf')) == row['preview_sha256']
        with zipfile.ZipFile(source) as before, zipfile.ZipFile(trial) as after:
            assert set(before.namelist()) == set(after.namelist())
            assert all(before.read(n) == after.read(n) for n in before.namelist() if n != 'word/document.xml')
            validate_change(E.fromstring(before.read('word/document.xml')),
                            E.fromstring(after.read('word/document.xml')), row['profile'])
        for suffix in ['.docx', '.pdf']:
            keep(trial.with_suffix(suffix), 'trials/' + trial.with_suffix(suffix).name)
        if row['profile'] == 'baseline':
            preview = a.prior / 'word-preview' / (stem + '.pdf')
            assert geometry(preview) == geometry(trial.with_suffix('.pdf')), 'Frozen baseline geometry drift'
            baseline_geometry.append({'case': row['case'], 'language': row['language'],
                                      'prior_preview_sha256': sha(preview), 'all_page_geometry_identical': True})
            keep(source, 'native-source/' + source.name)
            keep(source.with_suffix('.docx.fixture.json'), 'native-source/' + stem + '.docx.fixture.json')
    mixed = {r['profile']: r for r in report['rows'] if r['case'] == 'budget-mixed-gaps' and r['language'] == 'chinese'}
    assert all(r['pages'] == 8 for r in mixed.values())
    assert mixed['baseline']['anchors']['question'] == [7] and mixed['baseline']['anchors']['budget_heading'] == [8]
    assert mixed['release-budget-heading']['anchors']['budget_heading'] == [7]
    assert mixed['release-budget-heading']['anchors']['resource_1'] == [8]
    assert mixed['release-table-labels']['anchors']['resource_1'] == [7]
    assert mixed['release-table-labels']['anchors']['resource_1_end'] == [8]
    assert all(pages == [8] for pages in mixed['keep-overview']['anchors'].values())
    keep(a.trials / 'report.json', 'trials/report.json')
    for name in ['runner.py', 'report.json']:
        keep(a.earlier_trials / name, 'diagnostics/earlier-trials/' + name)
    for name in ['failed-runner.py', 'report.json']:
        keep(a.failed_trials / name, 'diagnostics/failed-first-trial/' + name)
    keep(a.prior / 'manifest.json', 'native-source/manifest.json')
    for name in ['rehearse_budget_tail.py', 'collect_budget_tail_review.py', 'check_word_short_budget_outputs.py',
                 'check_word_rhythm_outputs.py']:
        keep(ROOT / 'scripts' / name, 'reproduce/' + name)
    keep(ROOT / 'pipeline.yml', 'reproduce/pipeline.yml')
    a.destination.mkdir(parents=True, exist_ok=False)
    for source, relative in copies:
        target = a.destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    earlier = {str(f.relative_to(a.earlier_trials)): sha(f) for f in sorted(a.earlier_trials.iterdir()) if f.is_file()}
    (a.destination / 'diagnostics/earlier-trials/file-hashes.json').write_text(json.dumps(earlier, indent=2) + '\n')
    fonts = {}
    for family in ['Arial', 'Noto Sans CJK TC']:
        path = Path(subprocess.check_output(['fc-match', '-f', '%{file}', family], text=True))
        fonts[family] = {'actual_file': str(path), 'sha256': sha(path)}
    evidence = {'selected_checks_passed': True, 'release_acceptance': False, 'template_modified': False,
                'no_pagination_variant_adopted': True, 'baseline_geometry': baseline_geometry,
                'fonts': fonts, 'collector_sha256': sha(Path(__file__)),
                'limits': ['Negative experiment: does not fix blank tail pages',
                           'Per-block line geometry checks do not establish full visual acceptance',
                           'Repeated paragraph anchors can be ambiguous; the split-row finding also has visual review']}
    (a.destination / 'audit.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    print(a.destination)


if __name__ == '__main__':
    main()
