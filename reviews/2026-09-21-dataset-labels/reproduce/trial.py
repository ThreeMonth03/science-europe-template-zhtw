"""Build public label controls and an exact, non-release Jinja package trial."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(Path(__file__).parent)]
from artifact_utils import sha
from label_recipe import patch
from notice_recipe import BASE
from label_probe import run


def fixtures(english, previous, output):
    sys.path.insert(0, str(english / 'scripts'))
    from generate_pilot_fixtures import IDS, path
    assert not output.exists(); output.mkdir(parents=True)
    shutil.copytree(previous / 'knowledge-models', output / 'knowledge-models')
    for locale in ['en', 'zh-Hant']:
        folder = output / locale; folder.mkdir()
        recipe = json.loads((previous / locale / 'notice-mixed.json').read_text())
        values = {e['path']: e['value'] for e in json.loads((previous / locale / 'notice-mixed.events.json').read_text())}
        for key in list(values):
            if key.endswith(IDS['measuredDataNameQUuid']): del values[key]
        reference = path('reusingCUuid', 'preexistingQUuid', 'preexistingYesAUuid', 'refDataQUuid')
        first, second = values[reference]['value']
        values.pop(path(reference, second, 'refDataNameQUuid'))
        conditions = path(reference, first, 'refDataUseQUuid', 'refDataUseYesAUuid', 'refDataConditionsQUuid')
        for key in list(values):
            if key == conditions or key.startswith(conditions + '.'): del values[key]
        # Q8 now displays only original reference item 2. It must not become 1.
        produced = path('preservingCUuid', 'producedDataQUuid'); original = values[produced]['value'][0]
        clone = str(uuid.uuid5(uuid.NAMESPACE_URL, 'dataset-labels/produced-2'))
        prefix = path(produced, original)
        for key, value in list(values.items()):
            if key.startswith(prefix + '.'):
                values[path(produced, clone) + key[len(prefix):]] = copy.deepcopy(value)
        values[produced]['value'].append(clone)
        values.pop(path(produced, clone, 'producedDataNameQUuid'))
        # Named entries that look like generic labels are authored, not renamed.
        values[path(produced, original, 'producedDataNameQUuid')] = dict(type='StringReply', value='N/A')
        nonreference = path('reusingCUuid', 'preexistingQUuid', 'preexistingYesAUuid', 'nrefDataQUuid')
        item = str(uuid.uuid5(uuid.NAMESPACE_URL, 'dataset-labels/non-reference'))
        values[nonreference] = dict(type='ItemListReply', value=[item])
        use = path(nonreference, item, 'nrefDataUseQUuid')
        values[use] = dict(type='AnswerReply', value=IDS['nrefDataUseYesAUuid'])
        used = path(use, 'nrefDataUseYesAUuid')
        values[path(used, 'nrefDataConditionsQUuid')] = dict(type='AnswerReply', value=IDS['nrefDataConditionsCCBYAUuid'])
        values[path(used, 'nrefDataUsageQUuid')] = dict(type='StringReply', value='AUTHORED-NONREFERENCE: N/A / 0 / Original.csv.')
        neq = path('creatingCUuid', 'neqDataQUuid')
        values[neq] = dict(type='AnswerReply', value=IDS['neqDataYesAUuid'])
        neq_items = path(neq, 'neqDataYesAUuid', 'neqDataSetsQUuid')
        item = str(uuid.uuid5(uuid.NAMESPACE_URL, 'dataset-labels/non-equipment'))
        values[neq_items] = dict(type='ItemListReply', value=[item])
        values[path(neq_items, item, 'neqDataSetsDescQUuid')] = dict(type='StringReply', value='AUTHORED-NONEQUIPMENT: N/A / 0 / Original.csv.')
        events = [dict(type='SetReplyEvent', uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, 'dataset-labels/' + locale + '/' + key)), path=key, value=value)
                  for key, value in sorted(values.items(), key=lambda kv: (kv[0].count('.'), kv[0]))]
        target = folder / 'dataset-labels.events.json'; target.write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
        recipe.update(name='Public neutral dataset label trial', events_file=target.name)
        (folder / 'dataset-labels.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')


def packages(baseline, output):
    assert not output.exists(); output.mkdir(parents=True)
    manifest = json.loads((baseline / 'manifest.json').read_text())
    assert manifest['status'] == 'runtime-experiment'
    proof = dict(prototype_only=True, release_acceptance=False, global_switch_complete=False,
                 recipe_sha256=sha(Path(__file__).with_name('label_recipe.py')), packages={})
    for language in ['english', 'chinese']:
        name = language + '.zip'; assert sha(baseline / name) == BASE[name]
        with zipfile.ZipFile(baseline / name) as before, zipfile.ZipFile(output / name, 'w') as after:
            data, operations = patch(json.loads(before.read('template/template.json')), language)
            for entry in before.infolist():
                value = before.read(entry.filename)
                if entry.filename == 'template/template.json': value = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                after.writestr(entry, value)
        manifest['sha256'][name] = sha(output / name)
        proof['packages'][name] = dict(baseline_sha256=BASE[name], sha256=sha(output / name), operations=operations)
    manifest.pop('identical_package_sha256', None); manifest.update(prototype=proof, baseline_build=str(baseline.resolve()))
    for name, data in [('manifest.json', manifest), ('prototype.json', proof)]:
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=['fixtures', 'packages', 'probe'])
    for name in ['english', 'previous', 'baseline', 'fixtures']: p.add_argument('--' + name, type=Path)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    if a.action == 'fixtures': fixtures(a.english.resolve(), a.previous, a.output)
    elif a.action == 'packages': packages(a.baseline, a.output)
    else:
        assert not a.output.exists()
        proof = dict(passed=False, release_acceptance=False, global_switch_complete=False,
                     checker_sha256=sha(Path(__file__).with_name('label_probe.py')), recipe_sha256=sha(Path(__file__).with_name('label_recipe.py')))
        try: proof['rows'] = run(a.english.resolve(), a.fixtures); proof['passed'] = True
        except Exception as error: proof['failure'] = repr(error); raise
        finally: a.output.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(dict(passed=True, cases=len(proof['rows']))))


if __name__ == '__main__': main()
