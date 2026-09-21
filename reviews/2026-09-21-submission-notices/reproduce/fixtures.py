"""Public adversarial-looking prose and partial affirmative answers; no live data."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from artifact_utils import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--english', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    sys.path.insert(0, str(a.english.resolve() / 'scripts'))
    from generate_pilot_fixtures import IDS
    a.output.mkdir(parents=True)
    proof = dict(public_synthetic=True, generator_sha256=sha(Path(__file__)), rows=[])
    for locale in ['en', 'zh-Hant']:
        source = a.english / 'fixtures/pilot' / locale; folder = a.output / locale; folder.mkdir()
        recipe = json.loads((source / 'profile-partial.json').read_text())
        bundle = (source / recipe['knowledge_model_package_id']).resolve()
        km = a.output / 'knowledge-models' / bundle.name; km.parent.mkdir(exist_ok=True)
        shutil.copy2(bundle, km)
        values = {e['path']: e['value'] for e in json.loads((source / 'profile-partial.events.json').read_text())}
        paths = lambda field: [p for p in values if p.endswith(IDS[field])]
        def choose(path, answer): values[path] = dict(type='AnswerReply', value=IDS[answer])
        for path in paths('refDataConditionsQUuid'):
            choose(path, 'refDataConditionsOtherAUuid')
            for child in list(values):
                if child.startswith(path + '.'): del values[child]
        for path in paths('measuredDataQualityQUuid'):
            choose(path, 'measuredDataQualityYesAUuid')
            other = path + '.' + IDS['measuredDataQualityYesAUuid'] + '.' + IDS['mdQualityOtherQUuid']
            choose(other, 'mdQualityOtherYesAUuid')
            for child in list(values):
                if child.startswith(other + '.'): del values[child]
        for path in paths('isPublishedDataQUuid'):
            if values[path]['value'] == IDS['isPublishedDataYesAUuid']:
                software = path + '.' + IDS['isPublishedDataYesAUuid'] + '.' + IDS['publishedSpecSwUseQUuid']
                choose(software, 'publishedSpecSwUseYesAUuid')
                for child in list(values):
                    if child.startswith(software + '.'): del values[child]
        authored = next(p for p, v in values.items() if isinstance(v['value'], str) and ('Information not provided: this is authored' in v['value'] or '尚待補充：這是使用者填寫' in v['value']))
        values[authored]['value'] += '\n\n<p class="data-gap" data-fact-id="authored" data-status="missing">AUTHORED-NOTICE: 尚待補充 / Information not provided / N/A / 0 / Original.csv.</p>'
        events = [dict(type='SetReplyEvent', uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, 'submission-notices/' + locale + '/' + path)), path=path, value=value)
                  for path, value in sorted(values.items(), key=lambda pair: (pair[0].count('.'), pair[0]))]
        target = folder / 'notice-mixed.events.json'; target.write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
        recipe.update(name='Public marked-notice trial', events_file=target.name, knowledge_model_package_id='../knowledge-models/' + km.name)
        (folder / 'notice-mixed.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
        for name in ['empty', 'budget-long-no-currency']:
            original = json.loads((source / (name + '.json')).read_text())
            original['knowledge_model_package_id'] = '../knowledge-models/' + km.name
            (folder / (name + '.json')).write_text(json.dumps(original, ensure_ascii=False, indent=2) + '\n')
            shutil.copy2(source / (name + '.events.json'), folder / (name + '.events.json'))
        proof['rows'].append(dict(locale=locale, source_events_sha256=sha(source / 'profile-partial.events.json'),
                                 events_sha256=sha(target), knowledge_model_sha256=sha(km), authored_path=authored))
    (a.output / 'provenance.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')
    print(a.output)


if __name__ == '__main__': main()
