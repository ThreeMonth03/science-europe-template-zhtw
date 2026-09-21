"""Prepare exact local-DSW Word pipeline candidates; leave HTML/PDF unchanged."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from table_recipe import ROOT, HERE, ARCHIVE, IMAGE, LUA, baseline, patch, sha

sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_runtime_variant import require_tables_only_sources

CASES = ['ethics-missing', 'ethics-answered', 'ethics-long']


def packages(source, engine, output):
    assert not output.exists(); output.mkdir(parents=True)
    manifest = json.loads((source / 'manifest.json').read_text())
    frozen = json.loads((ARCHIVE / 'after/manifest.json').read_text())
    assert manifest['status'] == 'runtime-experiment'
    report = json.loads((engine / 'report.json').read_text()); assert report['passed']
    for name, digest in report['source_sha256'].items(): assert sha((HERE / name).read_bytes()) == digest
    runtime = json.loads((engine / 'runtime.json').read_text())
    assert runtime['pandoc'] == 'pandoc 3.8.3'
    observed = json.loads(subprocess.check_output(['docker', 'exec', 'science-europe-pilot-docworker-1', 'python', '-c',
        'import hashlib,importlib.util,json; from pathlib import Path; '
        'names=' + repr(list(runtime['sources']) + ['dsw.document_worker.model.utils', 'weasyprint.text.fonts', 'weasyprint.text.ffi']) + '; '
        'print(json.dumps({n:hashlib.sha256(Path(importlib.util.find_spec(n).origin).read_bytes()).hexdigest() for n in names}))'], text=True))
    extras = {k: observed.pop(k) for k in runtime['sources']}; assert extras == runtime['sources']
    require_tables_only_sources(observed)
    assert subprocess.check_output(['docker', 'inspect', '--format', '{{.Image}}', 'science-europe-pilot-docworker-1'], text=True).strip() == IMAGE
    proof = dict(prototype_only=True, source_integrated=False, release_acceptance=False,
                 observed_worker_sources=observed, observed_word_sources=extras,
                 recipe_sha256=sha((HERE / 'table_recipe.py').read_bytes()), packages={})
    for language in ['english', 'chinese']:
        name = language + '.zip'
        assert sha((source / name).read_bytes()) == manifest['sha256'][name] == frozen['sha256'][name]
        with zipfile.ZipFile(source / name) as original:
            old = json.loads(original.read('template/template.json')); assert old == baseline(language)
            new = patch(old, language); members = {n: sha(original.read(n)) for n in original.namelist()}
            with zipfile.ZipFile(output / name, 'w') as target:
                for entry in original.infolist():
                    value = original.read(entry.filename)
                    if entry.filename == 'template/template.json':
                        value = json.dumps(new, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                    target.writestr(copy.copy(entry), value)
                info = zipfile.ZipInfo('template/assets/' + LUA, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                target.writestr(info, (HERE / 'short-tables.lua').read_bytes())
        with zipfile.ZipFile(output / name) as z: after = {n: sha(z.read(n)) for n in z.namelist()}
        assert set(after) - set(members) == {'template/assets/' + LUA} and not (set(members) - set(after))
        assert {n for n in members if members[n] != after[n]} == {'template/template.json'}
        proof['packages'][name] = dict(baseline_sha256=sha((source / name).read_bytes()), sha256=sha((output / name).read_bytes()),
                                      before_members=members, after_members=after)
        manifest['sha256'][name] = sha((output / name).read_bytes())
    manifest.pop('identical_package_sha256', None); manifest.update(prototype=proof, baseline_build=str(source.resolve()))
    for name, value in [('manifest.json', manifest), ('prototype.json', proof)]:
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['source', 'engine', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); packages(a.source, a.engine, a.output)
