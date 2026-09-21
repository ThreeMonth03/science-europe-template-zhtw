"""Exact asset-path package trial on the owned localhost DSW only."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from asset_recipe import ROOT, HERE, ARCHIVE, XML, IMAGE, baseline, helper, patch, sha

sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_runtime_variant import require_tables_only_sources


def packages(source, output):
    assert not output.exists()
    manifest = json.loads((source / 'manifest.json').read_text())
    assert manifest == json.loads((ARCHIVE / 'after/manifest.json').read_text())
    runtime = json.loads((ARCHIVE / 'engine/runtime.json').read_text())
    expected = dict(runtime['sources'], **manifest['prototype']['observed_worker_sources'])
    observed = json.loads(subprocess.check_output(['docker', 'exec', 'science-europe-pilot-docworker-1', 'python', '-c',
        'import hashlib,importlib.util,json; from pathlib import Path; names=' + repr(list(expected)) + '; '
        'print(json.dumps({n:hashlib.sha256(Path(importlib.util.find_spec(n).origin).read_bytes()).hexdigest() for n in names}))'], text=True))
    assert observed == expected
    assert subprocess.check_output(['docker', 'inspect', '--format', '{{.Image}}', 'science-europe-pilot-docworker-1'], text=True).strip() == IMAGE
    require_tables_only_sources(manifest['prototype']['observed_worker_sources'])
    output.mkdir(parents=True)
    proof = dict(prototype_only=True, source_integrated=False, release_acceptance=False,
        observed_worker_sources=manifest['prototype']['observed_worker_sources'],
        observed_word_sources=runtime['sources'], recipe_sha256=sha((HERE / 'asset_recipe.py').read_bytes()), packages={})
    for language in ['english', 'chinese']:
        name = language + '.zip'; source_hash = sha((source / name).read_bytes())
        assert source_hash == manifest['sha256'][name]
        with zipfile.ZipFile(source / name) as original:
            old = json.loads(original.read('template/template.json')); assert old == baseline(language)
            new = patch(old, language); members = {n: sha(original.read(n)) for n in original.namelist()}
            with zipfile.ZipFile(output / name, 'w') as target:
                for entry in original.infolist():
                    value = original.read(entry.filename)
                    if entry.filename == 'template/template.json':
                        value = json.dumps(new, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                    target.writestr(copy.copy(entry), value)
                info = zipfile.ZipInfo('template/assets/' + XML, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED; target.writestr(info, helper())
        with zipfile.ZipFile(output / name) as z: after = {n: sha(z.read(n)) for n in z.namelist()}
        assert set(after) - set(members) == {'template/assets/' + XML} and set(members) <= set(after)
        assert {n for n in members if members[n] != after[n]} == {'template/template.json'}
        proof['packages'][name] = dict(baseline_sha256=source_hash, sha256=sha((output / name).read_bytes()),
            before_members=members, after_members=after)
        manifest['sha256'][name] = sha((output / name).read_bytes())
    manifest.update(prototype=proof, baseline_build=str(source.resolve()))
    for name, value in [('manifest.json', manifest), ('prototype.json', proof)]:
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); packages(a.source, a.output)
