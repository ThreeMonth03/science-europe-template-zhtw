"""Public missing/answered Q9 controls and exact package-only variants."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/entity-labels'), str(Path(__file__).parent)]
from artifact_utils import sha
from entity_trial import fixture_events as entity_events
from ethics_recipe import ARCHIVE, baseline, patch, TEXT
from ethics_probe import run

CASES = ['ethics-missing', 'ethics-answered']


def fixture_events(english, locale, case):
    assert case in CASES
    from generate_pilot_fixtures import IDS, path
    language = 'english' if locale == 'en' else 'chinese'
    values = {e['path']: e['value'] for e in entity_events(english, locale)}
    def choice(key, name): values[key] = dict(type='AnswerReply', value=IDS[name])
    personal = path('creatingCUuid', 'collectPersonalQUuid'); choice(personal, 'collectPersonalYesAUuid')
    gdpr = path(personal, 'collectPersonalYesAUuid', 'cpersGdprQUuid'); choice(gdpr, 'cpersGdprExploreAUuid')
    legal = path(gdpr, 'cpersGdprExploreAUuid', 'cpersGdprLegalBasisQUuid'); choice(legal, 'cpersGdprLegalBasisOtherAUuid')
    if case == 'ethics-answered':
        choice(path(legal, 'cpersGdprLegalBasisOtherAUuid', 'cpersGdprLegalBasisOtherWhichQUuid'),
               'cpersGdprLegalBasisOtherWhichContractAUuid')
        produced = path('preservingCUuid', 'producedDataQUuid')
        for i, item in enumerate(values[produced]['value']):
            choice(path(produced, item, 'containPersonalQUuid'), 'containPersonalYesAUuid' if i == 0 else 'containPersonalNoAUuid')
            choice(path(produced, item, 'containSensitiveQUuid'), 'containSensitiveNoAUuid' if i == 0 else 'containSensitiveYesAUuid')
    purpose = path(gdpr, 'cpersGdprExploreAUuid', 'cpersGdprPurposeQUuid')
    # Exact diagnostic lookalikes are authored controls, including the same
    # span/em shape as the owned dataset prompt, but under a different owner.
    authored = ('<p>AUTHORED-PURPOSE: N/A / 0 / Original.csv. '
        '<a href="https://example.org/ethics">https://example.org/ethics</a></p>'
        '<p>' + TEXT[language]['old'] + '</p>'
        '<p><span> - <em>' + TEXT[language]['flags'] + '</em></span></p>')
    values[purpose] = dict(type='StringReply', value=authored)
    return [dict(type='SetReplyEvent', uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, case + '/' + locale + '/' + key)),
        path=key, value=value) for key, value in sorted(values.items(), key=lambda kv: (kv[0].count('.'), kv[0]))]


def fixtures(english, models, output):
    assert not output.exists(); output.mkdir(parents=True)
    shutil.copytree(models, output / 'knowledge-models')
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
    for locale in ['en', 'zh-Hant']:
        folder = output / locale; folder.mkdir()
        for case in CASES:
            data = fixture_events(english, locale, case)
            (folder / (case + '.events.json')).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
            recipe = json.loads((ARCHIVE / 'fixtures' / locale / 'entity-labels.json').read_text())
            recipe.update(name='Public Q9 prompt ownership controls / ' + case, events_file=case + '.events.json')
            (folder / (case + '.json')).write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')


def packages(source, output, phase):
    assert phase in ['before', 'after'] and not output.exists(); output.mkdir(parents=True)
    manifest = json.loads((source / 'manifest.json').read_text()); assert manifest['status'] == 'runtime-experiment'
    frozen_manifest = json.loads((ARCHIVE / 'after/manifest.json').read_text())
    from prepare_runtime_variant import require_tables_only_sources
    observed = json.loads(subprocess.check_output(['docker', 'exec', 'science-europe-pilot-docworker-1', 'python', '-c',
        "import hashlib,importlib.util,json; from pathlib import Path; "
        "names=['dsw.document_worker.model.utils','weasyprint.text.fonts','weasyprint.text.ffi']; "
        "print(json.dumps({n:hashlib.sha256(Path(importlib.util.find_spec(n).origin).read_bytes()).hexdigest() for n in names}))"], text=True))
    require_tables_only_sources(observed)
    assert observed == manifest['runtime_variant']['reviewed_source_sha256']
    proof = dict(prototype_only=True, source_integrated=False, release_acceptance=False, global_switch_complete=False,
                 phase=phase, observed_worker_sources=observed,
                 recipe_sha256=sha(Path(__file__).with_name('ethics_recipe.py')), packages={})
    for language in ['english', 'chinese']:
        name = language + '.zip'; assert sha(source / name) == manifest['sha256'][name] == frozen_manifest['sha256'][name]
        with zipfile.ZipFile(source / name) as before:
            old = json.loads(before.read('template/template.json')); assert old == baseline(language)
            new, operations = patch(old, language) if phase == 'after' else (old, {})
            original_members = {n: hashlib.sha256(before.read(n)).hexdigest() for n in before.namelist()}
            if phase == 'before': shutil.copy2(source / name, output / name)
            else:
                with zipfile.ZipFile(output / name, 'w') as after:
                    for entry in before.infolist():
                        value = before.read(entry.filename)
                        if entry.filename == 'template/template.json':
                            value = json.dumps(new, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                        after.writestr(copy.copy(entry), value)
        with zipfile.ZipFile(output / name) as after:
            members = {n: dict(before=original_members[n], after=hashlib.sha256(after.read(n)).hexdigest()) for n in after.namelist()}
        assert {n for n, d in members.items() if d['before'] != d['after']} == ({'template/template.json'} if phase == 'after' else set())
        proof['packages'][name] = dict(baseline_sha256=sha(source / name), sha256=sha(output / name), operations=operations, members=members)
        manifest['sha256'][name] = sha(output / name)
    manifest.pop('identical_package_sha256', None)
    manifest.update(prototype=proof, baseline_build=str(source.resolve()))
    for name, data in [('manifest.json', manifest), ('prototype.json', proof)]:
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=['fixtures', 'packages', 'probe'])
    for name in ['english', 'models', 'source', 'fixtures']: p.add_argument('--' + name, type=Path)
    p.add_argument('--phase', choices=['before', 'after']); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.action == 'fixtures': fixtures(a.english.resolve(), a.models, a.output)
    elif a.action == 'packages': packages(a.source, a.output, a.phase)
    else:
        assert not a.output.exists()
        proof = dict(passed=False, prototype_only=True, source_integrated=False, native_checked=False,
            release_acceptance=False, checker_sha256=sha(Path(__file__).with_name('ethics_probe.py')),
            recipe_sha256=sha(Path(__file__).with_name('ethics_recipe.py')))
        try: proof['rows'] = run(a.english.resolve(), a.fixtures); proof['passed'] = True
        except Exception as error: proof['failure'] = repr(error); raise
        finally: a.output.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(dict(passed=True, checks=len(proof['rows']))))


if __name__ == '__main__': main()
