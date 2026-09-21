"""Exact Q9 lead package variants and a public long-first-paragraph control."""
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
from lead_recipe import ROOT, ARCHIVE, baseline, patch

sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/ethics-prompts')]
from artifact_utils import sha
from lead_probe import run

CASES = ['ethics-missing', 'ethics-answered', 'ethics-long']
AUTHORED_START = 'AUTHORED-PURPOSE: N/A / 0 / Original.csv.'
AUTHORED_END = 'END-OF-LONG-FIRST-PARAGRAPH.'


def fixtures(english, models, output):
    assert not output.exists(); output.mkdir(parents=True)
    shutil.copytree(models, output / 'knowledge-models')
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
    from generate_pilot_fixtures import path
    for locale in ['en', 'zh-Hant']:
        folder = output / locale; folder.mkdir()
        for case in CASES[:2]:
            for suffix in ['.json', '.events.json']:
                shutil.copy2(ARCHIVE / 'fixtures' / locale / (case + suffix), folder / (case + suffix))
        events = json.loads((folder / 'ethics-missing.events.json').read_text())
        purpose = path('creatingCUuid', 'collectPersonalQUuid', 'collectPersonalYesAUuid', 'cpersGdprQUuid',
                       'cpersGdprExploreAUuid', 'cpersGdprPurposeQUuid')
        sentence = ('This is public synthetic text for a page-break test; N/A and 0 remain literal. ' if locale == 'en'
                    else '這是用於跨頁測試的公開合成文字；N/A 與 0 均須原樣保留，不代表研究計畫的承諾。')
        answer = ('<p>' + AUTHORED_START + ' ' + ''.join('[' + str(i) + '] ' + sentence for i in range(1, 151))
                  + AUTHORED_END + '</p><ul><li>LIST-A: N/A.</li><li>LIST-B: 0.</li></ul>'
                  '<table><thead><tr><th>Item</th><th>Value</th></tr></thead><tbody>'
                  '<tr><td>Original.csv</td><td>0</td></tr><tr><td>N/A</td><td>Retained.</td></tr></tbody></table>'
                  '<p>FINAL-AUTHORED-PARAGRAPH: <a href="https://example.org/ethics">https://example.org/ethics</a></p>')
        for event in events:
            if event['path'] == purpose: event['value']['value'] = answer
            event['uuid'] = str(uuid.uuid5(uuid.NAMESPACE_URL, 'ethics-long/' + locale + '/' + event['path']))
        (folder / 'ethics-long.events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
        recipe = json.loads((folder / 'ethics-missing.json').read_text())
        recipe.update(name='Public Q9 long first paragraph with list/table continuation', events_file='ethics-long.events.json')
        (folder / 'ethics-long.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')


def packages(source, output, phase):
    assert phase in ['before', 'after'] and not output.exists(); output.mkdir(parents=True)
    manifest = json.loads((source / 'manifest.json').read_text()); assert manifest['status'] == 'runtime-experiment'
    frozen = json.loads((ARCHIVE / 'after/manifest.json').read_text())
    from prepare_runtime_variant import require_tables_only_sources
    observed = json.loads(subprocess.check_output(['docker', 'exec', 'science-europe-pilot-docworker-1', 'python', '-c',
        'import hashlib,importlib.util,json; from pathlib import Path; '
        "names=['dsw.document_worker.model.utils','weasyprint.text.fonts','weasyprint.text.ffi']; "
        'print(json.dumps({n:hashlib.sha256(Path(importlib.util.find_spec(n).origin).read_bytes()).hexdigest() for n in names}))'], text=True))
    require_tables_only_sources(observed)
    assert observed == manifest['runtime_variant']['reviewed_source_sha256']
    proof = dict(prototype_only=True, source_integrated=False, release_acceptance=False, phase=phase,
                 observed_worker_sources=observed, recipe_sha256=sha(Path(__file__).with_name('lead_recipe.py')), packages={})
    for language in ['english', 'chinese']:
        name = language + '.zip'; assert sha(source / name) == manifest['sha256'][name] == frozen['sha256'][name]
        with zipfile.ZipFile(source / name) as original:
            old = json.loads(original.read('template/template.json')); assert old == baseline(language)
            new, operations = patch(old, language) if phase == 'after' else (old, {})
            original_members = {n: hashlib.sha256(original.read(n)).hexdigest() for n in original.namelist()}
            if phase == 'before': shutil.copy2(source / name, output / name)
            else:
                with zipfile.ZipFile(output / name, 'w') as target:
                    for entry in original.infolist():
                        value = original.read(entry.filename)
                        if entry.filename == 'template/template.json':
                            value = json.dumps(new, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                        target.writestr(copy.copy(entry), value)
        with zipfile.ZipFile(output / name) as target:
            members = {n: dict(before=original_members[n], after=hashlib.sha256(target.read(n)).hexdigest()) for n in target.namelist()}
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
        sys.path[:0] = [str(a.english.resolve() / 'scripts'), str(a.english.resolve() / 'tests')]
        assert not a.output.exists()
        proof = dict(passed=False, prototype_only=True, source_integrated=False, native_checked=False,
            checker_sha256=sha(Path(__file__).with_name('lead_probe.py')), recipe_sha256=sha(Path(__file__).with_name('lead_recipe.py')))
        try: proof['rows'] = run(a.english.resolve(), a.fixtures); proof['passed'] = True
        except Exception as error: proof['failure'] = repr(error); raise
        finally: a.output.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(dict(passed=True, checks=len(proof['rows']))))


if __name__ == '__main__': main()
