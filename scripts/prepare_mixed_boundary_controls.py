"""Public position/count controls derived from the unchanged locked fixtures."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys
import uuid
from artifact_utils import sha
from generate_mixed_budget_fixtures import cases as mixed_cases

CASES = ['mixed-long-first', 'mixed-long-middle', 'mixed-small-groups',
         'mixed-bound-32-first', 'mixed-bound-33-last']


def cases(folder, ids):
    mixed = mixed_cases(folder, ids)
    result = {name: mixed[name] for name in CASES[:3]}
    for count, name in [(32, CASES[3]), (33, CASES[4])]:
        replies = copy.deepcopy(mixed['mixed-long-last'])
        cost = next(p for p in replies if p.endswith(ids['costQUuid']))
        items = list(replies[cost]['value']); ordinary, long = items[:-1], items[-1]
        first = cost + '.' + ordinary[0]
        fields = {p[len(first):]: copy.deepcopy(v) for p, v in replies.items() if p.startswith(first + '.')}
        assert fields and len(ordinary) == 8
        for number in range(10, count + 1):
            item = str(uuid.uuid5(uuid.NAMESPACE_URL, 'science-europe/mixed-boundary/' + str(number)))
            prefix = cost + '.' + item
            for suffix, value in fields.items(): replies[prefix + suffix] = copy.deepcopy(value)
            replies[prefix + '.' + ids['costTitleQUuid']]['value'] = (
                f'Boundary resource {number}' if folder.name == 'en' else f'邊界測試資源 {number}')
            replies[prefix + '.' + ids['costAmountQUuid']]['value'] = str(number * 100)
            ordinary.append(item)
        replies[cost]['value'] = [long] + ordinary if count == 32 else ordinary + [long]
        assert len(replies[cost]['value']) == len(set(replies[cost]['value'])) == count
        result[name] = replies
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--english', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    sys.path.insert(0, str(a.english.resolve() / 'scripts'))
    from generate_pilot_fixtures import IDS
    a.output.mkdir(parents=True)
    report = dict(public_synthetic=True, source_repo_modified=False,
                  generator_sha256=sha(Path(__file__)), parent_generator_sha256=sha(Path(__file__).with_name('generate_mixed_budget_fixtures.py')),
                  inputs={}, cases={})
    for locale in ['en', 'zh-Hant']:
        folder = a.english / 'fixtures/pilot' / locale; target = a.output / locale; target.mkdir()
        recipe = json.loads((folder / 'budget-many.json').read_text())
        source_km = (folder / recipe['knowledge_model_package_id']).resolve()
        km = a.output / 'knowledge-models' / source_km.name; km.parent.mkdir(exist_ok=True)
        if not km.exists(): shutil.copy2(source_km, km)
        assert sha(km) == sha(source_km)
        report['inputs'][locale] = {n: sha(folder / n) for n in ['budget-many.json', 'budget-many.events.json', 'budget-long.events.json']}
        for name, replies in cases(folder, IDS).items():
            events = [dict(type='SetReplyEvent', uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, 'mixed-boundary/' + locale + '/' + name + '/' + path)),
                           path=path, value=value) for path, value in sorted(replies.items(), key=lambda item: (item[0].count('.'), item[0]))]
            event_path = target / (name + '.events.json')
            event_path.write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
            selected = dict(recipe, name='Public position and boundary QA / ' + name,
                events_file=event_path.name, knowledge_model_package_id='../knowledge-models/' + km.name)
            recipe_path = target / (name + '.json')
            recipe_path.write_text(json.dumps(selected, ensure_ascii=False, indent=2) + '\n')
            report['cases'][locale + '/' + name] = dict(recipe_sha256=sha(recipe_path), events_sha256=sha(event_path),
                km_sha256=sha(km), reply_count=len(events))
    (a.output / 'provenance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(a.output)


if __name__ == '__main__': main()
