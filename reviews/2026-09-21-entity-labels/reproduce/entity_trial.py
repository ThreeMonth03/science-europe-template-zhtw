"""Prepare synthetic entity controls and exact non-release package variants."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(Path(__file__).parent)]
from artifact_utils import sha
from entity_recipe import baseline as frozen, patch, BASELINE
from entity_probe import run


def fixture_events(english, locale):
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
    from generate_pilot_fixtures import IDS, path
    values = {}
    def put(key, value, kind='StringReply'): values[key] = dict(type=kind, value=value)
    def choice(key, name): put(key, IDS[name], 'AnswerReply')
    def items(key, label, count):
        result = [str(uuid.uuid5(uuid.NAMESPACE_URL, 'entity-labels/' + label + '/' + str(i))) for i in range(1, count + 1)]
        put(key, result, 'ItemListReply'); return result
    projects = path('adminDetailsCUuid', 'projectsQUuid')
    project_ids = items(projects, 'project', 3)
    put(path(projects, project_ids[0], 'projectNameQUuid'), 'N/A')
    for project_index, project in enumerate(project_ids[1:], 2):
        prefix = path(projects, project)
        put(path(prefix, 'projectNumberQUuid'), '0' if project_index == 2 else 'TW-3')
        text = ('AUTHORED-PROJECT: 尚待補充 / N/A / 0 / Original.csv.' if locale == 'zh-Hant'
                else 'AUTHORED-PROJECT: Information not provided / N/A / 0 / Original.csv.')
        put(path(prefix, 'projectAbstractQUuid'), text)
        choice(path(prefix, 'projEthicalApprovalQUuid'),
               'projEthicalApprovalNoAUuid' if project_index == 2 else 'projEthicalApprovalYesAUuid')
        costs = path(prefix, 'costQUuid')
        for cost_index, cost in enumerate(items(costs, 'project-' + str(project_index) + '-resource', 2), 1):
            c = path(costs, cost)
            if cost_index == 1:
                put(path(c, 'costTitleQUuid'), '(no resource name given)' if locale == 'en' else '（尚未填寫資源名稱）')
            put(path(c, 'costDescriptionQUuid'), 'AUTHORED-RESOURCE-' + str(project_index) + '-' + str(cost_index)
                + ': N/A / 0 / Original.csv. https://example.org/resource')
            put(path(c, 'costAmountQUuid'), '0')
            put(path(c, 'costAllocationQUuid'), [IDS['costManagementAUuid']], 'MultiChoiceReply')
            cover = path(c, 'costCoverQUuid'); choice(cover, 'costCoverOtherAUuid')
            put(path(cover, 'costCoverOtherAUuid', 'costCoverOtherHowQUuid'), 'AUTHORED-FUNDING: N/A')
    produced = path('preservingCUuid', 'producedDataQUuid')
    for dataset_index, dataset in enumerate(items(produced, 'dataset', 2), 1):
        d = path(produced, dataset)
        put(path(d, 'producedDataNameQUuid'), 'Original-' + str(dataset_index) + '.csv')
        publication = path(d, 'isPublishedDataQUuid'); choice(publication, 'isPublishedDataYesAUuid')
        use = path(publication, 'isPublishedDataYesAUuid', 'publishedSpecSwUseQUuid')
        choice(use, 'publishedSpecSwUseYesAUuid')
        software = path(use, 'publishedSpecSwUseYesAUuid', 'publishedSpecSwUseWhatQUuid')
        for tool_index, tool in enumerate(items(software, 'dataset-' + str(dataset_index) + '-tool', 3), 1):
            s = path(software, tool)
            if tool_index != 2:
                put(path(s, 'publishedSpecSwUseWhatNameQUuid'), 'N/A' if tool_index == 1 else
                    ('Software tool 2' if locale == 'en' else '軟體工具 2'))
            put(path(s, 'publishedSpecSwUseWhatPIDQUuid'), 'https://example.org/tool/' + str(dataset_index) + '/' + str(tool_index))
    return [dict(type='SetReplyEvent', uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, 'entity-labels/' + locale + '/' + key)),
                 path=key, value=value) for key, value in sorted(values.items(), key=lambda kv: (kv[0].count('.'), kv[0]))]


def fixtures(english, models, output):
    assert not output.exists(); output.mkdir(parents=True)
    shutil.copytree(models, output / 'knowledge-models')
    for locale in ['en', 'zh-Hant']:
        folder = output / locale; folder.mkdir()
        events = fixture_events(english, locale)
        (folder / 'entity-labels.events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
        recipe = json.loads((BASELINE / 'fixtures' / locale / 'empty.json').read_text())
        recipe.update(name='Public entity identity controls', events_file='entity-labels.events.json')
        (folder / 'entity-labels.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')


def packages(baseline, output):
    assert not output.exists(); output.mkdir(parents=True)
    manifest = json.loads((baseline / 'manifest.json').read_text())
    assert manifest['status'] == 'runtime-experiment'
    proof = dict(prototype_only=True, source_integrated=False, release_acceptance=False,
        global_switch_complete=False, recipe_sha256=sha(Path(__file__).with_name('entity_recipe.py')), packages={})
    for language in ['english', 'chinese']:
        name = language + '.zip'; assert sha(baseline / name) == manifest['sha256'][name]
        frozen_manifest = json.loads((BASELINE / 'native/manifest.json').read_text())
        assert manifest['sha256'][name] == frozen_manifest['sha256'][name], 'Unapproved ZIP or assets'
        with zipfile.ZipFile(baseline / name) as before, zipfile.ZipFile(output / name, 'w') as after:
            data = json.loads(before.read('template/template.json')); assert data == frozen(language)
            changed, operations = patch(data, language)
            members = {}
            for entry in before.infolist():
                value = before.read(entry.filename)
                before_digest = hashlib.sha256(value).hexdigest()
                if entry.filename == 'template/template.json':
                    value = json.dumps(changed, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                after.writestr(entry, value)
                members[entry.filename] = dict(before=before_digest, after=hashlib.sha256(value).hexdigest())
        proof['packages'][name] = dict(baseline_sha256=sha(baseline / name), sha256=sha(output / name),
                                      operations=operations, members=members)
        manifest['sha256'][name] = sha(output / name)
    manifest.pop('identical_package_sha256', None)
    manifest.update(prototype=proof, baseline_build=str(baseline.resolve()))
    for name, data in [('manifest.json', manifest), ('prototype.json', proof)]:
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=['fixtures', 'packages', 'probe'])
    for name in ['english', 'models', 'baseline', 'fixtures']: p.add_argument('--' + name, type=Path)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    if a.action == 'fixtures': fixtures(a.english.resolve(), a.models, a.output)
    elif a.action == 'packages': packages(a.baseline, a.output)
    else:
        assert not a.output.exists()
        proof = dict(passed=False, prototype_only=True, source_integrated=False, native_checked=False,
                     release_acceptance=False, checker_sha256=sha(Path(__file__).with_name('entity_probe.py')))
        try: proof['rows'] = run(a.english.resolve(), a.fixtures); proof['passed'] = True
        except Exception as error: proof['failure'] = repr(error); raise
        finally: a.output.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(dict(passed=True, checks=len(proof['rows']))))


if __name__ == '__main__': main()
