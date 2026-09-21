"""Public native controls: literal N/A versus missing fields, grants and quality."""
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
    p.add_argument('--english', type=Path, required=True); p.add_argument('--previous', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args(); assert not a.output.exists()
    sys.path.insert(0, str(a.english.resolve() / 'scripts'))
    from generate_pilot_fixtures import IDS, path
    a.output.mkdir(parents=True)
    shutil.copytree(a.previous / 'knowledge-models', a.output / 'knowledge-models')
    proof = dict(public_synthetic=True, generator_sha256=sha(Path(__file__)), rows=[])
    for locale in ['en', 'zh-Hant']:
        folder = a.output / locale; folder.mkdir()
        for case in ['empty', 'notice-mixed']:
            for suffix in ['.json', '.events.json']:
                shutil.copy2(a.previous / locale / (case + suffix), folder / (case + suffix))
        values = {e['path']: e['value'] for e in json.loads((folder / 'notice-mixed.events.json').read_text())}
        projects = path('adminDetailsCUuid', 'projectsQUuid')
        existing = values[projects]['value']; assert len(existing) == 1
        # Literal N/A in one field must survive while adjacent absent dates vanish.
        first = projects + '.' + existing[0]
        values[path(first, 'projectNumberQUuid')] = dict(type='StringReply', value='N/A')
        values.pop(path(first, 'projectStartQUuid'), None)
        for field in list(values):
            if field.endswith(IDS['grantNumberQUuid']): del values[field]
        for index in [2, 3]:
            item = str(uuid.uuid5(uuid.NAMESPACE_URL, 'submission-polish/project-' + str(index)))
            existing.append(item); prefix = projects + '.' + item
            title = 'N/A' if index == 2 else ('Information not provided' if locale == 'en' else '尚待補充')
            values[path(prefix, 'projectNameQUuid')] = dict(type='StringReply', value=title)
            if index == 2:
                values[path(prefix, 'projectStartQUuid')] = dict(type='StringReply', value='2026-09-21')
            values[path(prefix, 'projectAbstractQUuid')] = dict(type='StringReply', value='AUTHORED-OVERVIEW-' + str(index) + ': N/A / 0 / Original.csv.')
        # notice-mixed covers Other only; this case adds fixed methods in Q1/Q4.
        quality_paths = sorted(p for p in values if p.endswith(IDS['measuredDataQualityQUuid']))
        assert quality_paths
        prefix = quality_paths[0] + '.' + IDS['measuredDataQualityYesAUuid']
        for field in ['mdQualityCalibrating', 'mdQualityValidation']:
            values[path(prefix, field + 'QUuid')] = dict(type='AnswerReply', value=IDS[field + 'YesAUuid'])
        # Remove the actual instrument-list reply, not the measurement decision.
        for key in list(values):
            if IDS['measuredDataInstrQUuid'] in key.split('.'):
                del values[key]
        target = folder / 'submission-metadata.events.json'
        events = [dict(type='SetReplyEvent', uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, 'submission-polish/' + locale + '/' + key)), path=key, value=value)
                  for key, value in sorted(values.items(), key=lambda kv: (kv[0].count('.'), kv[0]))]
        target.write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
        recipe = json.loads((folder / 'notice-mixed.json').read_text())
        recipe.update(name='Public overview and quality submission trial', events_file=target.name)
        (folder / 'submission-metadata.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
        proof['rows'].append(dict(locale=locale, events_sha256=sha(target), source_sha256=sha(folder / 'notice-mixed.events.json')))
    (a.output / 'provenance.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')
    print(a.output)


if __name__ == '__main__': main()
