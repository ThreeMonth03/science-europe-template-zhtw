"""Assemble unchanged, sealed public fixtures for the integrated native run."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]
CASES = ['empty', 'notice-mixed', 'submission-metadata', 'dataset-labels']
ARCHIVES = {
    'polish': ('2026-09-21-submission-polish', '8005c0c66c6ad34582ca43b0e6fdba67045dee7d0b3894bd71ffba144771adf6'),
    'labels': ('2026-09-21-dataset-labels', 'c81445f317934ec5c3902d71a293f89034e4aa6980cc9104759973da976cd45a'),
}


def archive_for(case):
    name, seal = ARCHIVES['labels' if case == 'dataset-labels' else 'polish']
    return ROOT / 'reviews' / name, seal


def prepare(models):
    for name, seal in ARCHIVES.values():
        root = ROOT / 'reviews' / name
        assert sha(root / 'checksums.json') == seal
        for filename, digest in json.loads((root / 'checksums.json').read_text()).items():
            assert sha(root / filename) == digest, filename
    output = Path(tempfile.mkdtemp(prefix='submission-native-fixtures-', dir=ROOT / 'outputs'))
    (output / 'knowledge-models').mkdir()
    report = dict(public_synthetic=True, generator_sha256=sha(Path(__file__)), rows=[])
    for locale, language in [('en', 'english'), ('zh-Hant', 'chinese')]:
        folder = output / locale; folder.mkdir()
        for case in CASES:
            archive, seal = archive_for(case)
            source = archive / 'fixtures' / locale
            recipe = json.loads((source / (case + '.json')).read_text())
            assert recipe['events_file'] == case + '.events.json'
            bundle_name = Path(recipe['knowledge_model_package_id']).name
            assert recipe['knowledge_model_package_id'] == '../knowledge-models/' + bundle_name
            receipt = json.loads((archive / 'after/renders' / (case + '-review-' + language + '.html.fixture.json')).read_text())
            assert sha(source / (case + '.json')) == receipt['recipe_sha256']
            assert sha(source / recipe['events_file']) == receipt['events_sha256']
            assert sha(models / bundle_name) == receipt['km_sha256']
            for name in [case + '.json', recipe['events_file']]: shutil.copy2(source / name, folder / name)
            destination = output / 'knowledge-models' / bundle_name
            if destination.exists(): assert sha(destination) == receipt['km_sha256']
            else: shutil.copy2(models / bundle_name, destination)
            report['rows'].append(dict(case=case, language=language, archive=str(archive.relative_to(ROOT)),
                seal_sha256=seal, **{k: receipt[k] for k in ['recipe_sha256', 'events_sha256', 'km_sha256']}))
    (output / 'provenance.json').write_text(json.dumps(report, indent=2) + '\n')
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--models', type=Path, required=True)
    print(prepare(p.parse_args().models))
