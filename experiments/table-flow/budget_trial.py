"""New local package variants: only the Q15 template file changes."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from budget_recipe import ROOT, ARCHIVE, baseline, patch

sys.path[:0] = [str(ROOT / 'scripts')]
from artifact_utils import sha
from budget_probe import run

CASES = ['ethics-missing', 'ethics-answered', 'ethics-long']


def packages(source, output):
    assert not output.exists(); output.mkdir(parents=True)
    manifest = json.loads((source / 'manifest.json').read_text()); assert manifest['status'] == 'runtime-experiment'
    frozen = json.loads((ARCHIVE / 'after/manifest.json').read_text())
    from prepare_runtime_variant import require_tables_only_sources
    observed = json.loads(subprocess.check_output(['docker', 'exec', 'science-europe-pilot-docworker-1', 'python', '-c',
        'import hashlib,importlib.util,json; from pathlib import Path; '
        "names=['dsw.document_worker.model.utils','weasyprint.text.fonts','weasyprint.text.ffi']; "
        'print(json.dumps({n:hashlib.sha256(Path(importlib.util.find_spec(n).origin).read_bytes()).hexdigest() for n in names}))'], text=True))
    require_tables_only_sources(observed)
    assert observed == manifest['runtime_variant']['reviewed_source_sha256']
    proof = dict(prototype_only=True, source_integrated=False, release_acceptance=False,
                 observed_worker_sources=observed, recipe_sha256=sha(Path(__file__).with_name('budget_recipe.py')), packages={})
    for language in ['english', 'chinese']:
        name = language + '.zip'; assert sha(source / name) == manifest['sha256'][name] == frozen['sha256'][name]
        with zipfile.ZipFile(source / name) as original:
            old = json.loads(original.read('template/template.json')); assert old == baseline(language)
            new, operations = patch(old, language)
            original_members = {n: hashlib.sha256(original.read(n)).hexdigest() for n in original.namelist()}
            with zipfile.ZipFile(output / name, 'w') as target:
                for entry in original.infolist():
                    value = original.read(entry.filename)
                    if entry.filename == 'template/template.json':
                        value = json.dumps(new, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                    target.writestr(copy.copy(entry), value)
        with zipfile.ZipFile(output / name) as target:
            members = {n: dict(before=original_members[n], after=hashlib.sha256(target.read(n)).hexdigest()) for n in target.namelist()}
        assert {n for n, d in members.items() if d['before'] != d['after']} == {'template/template.json'}
        proof['packages'][name] = dict(baseline_sha256=sha(source / name), sha256=sha(output / name), operations=operations, members=members)
        manifest['sha256'][name] = sha(output / name)
    manifest.pop('identical_package_sha256', None)
    manifest.update(prototype=proof, baseline_build=str(source.resolve()))
    for name, data in [('manifest.json', manifest), ('prototype.json', proof)]:
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=['packages', 'probe'])
    for name in ['english', 'source', 'fixtures']: p.add_argument('--' + name, type=Path)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    if a.action == 'packages': packages(a.source, a.output)
    else:
        sys.path[:0] = [str(a.english.resolve() / 'scripts'), str(a.english.resolve() / 'tests')]
        assert not a.output.exists()
        proof = dict(passed=False, prototype_only=True, source_integrated=False, native_checked=False,
            checker_sha256=sha(Path(__file__).with_name('budget_probe.py')), recipe_sha256=sha(Path(__file__).with_name('budget_recipe.py')))
        try: proof['rows'] = run(a.english.resolve(), a.fixtures); proof['passed'] = True
        except Exception as error: proof['failure'] = repr(error); raise
        finally: a.output.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(dict(passed=True, checks=len(proof['rows']))))
