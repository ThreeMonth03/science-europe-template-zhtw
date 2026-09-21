"""Copy locked public controls and derive a genuinely single-row long fixture."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys
import uuid
from artifact_utils import sha

CASES = ['empty', 'profile-partial', 'budget-many', 'budget-long-no-currency', 'budget-single-long']


def single_long(events, cost_id):
    result = copy.deepcopy(events)
    cost = [e for e in result if e['path'].endswith(cost_id)]
    assert len(cost) == 1 and len(cost[0]['value']['value']) == 2
    path = cost[0]['path']; first, second = cost[0]['value']['value']
    cost[0]['value']['value'] = [first]
    removed = [e for e in result if e['path'].startswith(path + '.' + second + '.')]
    assert removed
    result = [e for e in result if e not in removed]
    for event in result:
        event['uuid'] = str(uuid.uuid5(uuid.NAMESPACE_URL, 'header-single-long/' + event['path']))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--english', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    sys.path.insert(0, str(a.english.resolve() / 'scripts'))
    from generate_pilot_fixtures import IDS
    a.output.mkdir(parents=True)
    report = {'public_synthetic': True, 'source_tree_modified': False,
              'generator_sha256': sha(Path(__file__)), 'cases': []}
    for locale in ['en', 'zh-Hant']:
        source = a.english / 'fixtures/pilot' / locale
        folder = a.output / locale; folder.mkdir()
        for case in CASES:
            original = 'budget-long' if case == 'budget-single-long' else case
            recipe_path = source / (original + '.json')
            recipe = json.loads(recipe_path.read_text())
            events_path = source / recipe['events_file']
            bundle = (source / recipe['knowledge_model_package_id']).resolve()
            km = a.output / 'knowledge-models' / bundle.name; km.parent.mkdir(exist_ok=True)
            if not km.exists(): shutil.copy2(bundle, km)
            assert sha(km) == sha(bundle)
            events = folder / (case + '.events.json')
            if case == 'budget-single-long':
                value = single_long(json.loads(events_path.read_text()), IDS['costQUuid'])
                events.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
            else:
                shutil.copy2(events_path, events)
            recipe.update(events_file=events.name, knowledge_model_package_id='../knowledge-models/' + km.name)
            # Keep all original title/answer text; changing fixture filenames is not a template change.
            target = folder / (case + '.json')
            target.write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
            report['cases'].append({'case': case, 'locale': locale, 'derived_from': original,
                'source_recipe_sha256': sha(recipe_path), 'source_events_sha256': sha(events_path),
                'recipe_sha256': sha(target), 'events_sha256': sha(events), 'km_sha256': sha(km)})
    (a.output / 'provenance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(a.output)


if __name__ == '__main__': main()
