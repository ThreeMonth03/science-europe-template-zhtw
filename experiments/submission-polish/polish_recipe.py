"""Bounded second-stage source trial: overview gaps and repetitive quality prose.

The previous marked-notice recipe remains frozen. This layer is reversible and
does not remove words from rendered answers, rewrite names, or release a DT.
"""
import argparse
import copy
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/submission-notices')]
from artifact_utils import sha
from notice_recipe import BASE, patch as marked_patch, project as reverse

REVIEW = "output_profile|default('review') != 'submission'"
SUBMIT = "output_profile|default('review') == 'submission'"
OTHER = 'otherAnswer == uuids.mdQualityOtherYesAUuid and not otherText'
WORDS = {
    'english': dict(instruments='No instruments for this dataset have been specified.',
        other='Other quality control methods are planned for <strong>{{ qualityName }}</strong>.',
        mixed='Quality control measures planned for <strong>{{ qualityName }}</strong>: <span data-fact-id="quality-methods" data-status="complete">{{ qualityMethods|join(", ") }}</span> and other quality control methods.'),
    'chinese': dict(instruments='尚未指定此資料集使用的儀器。',
        other='本計畫將對<strong>{{ qualityName }}</strong>採取其他品質管控方法。',
        mixed='<strong>{{ qualityName }}</strong>的品質管控措施包括<span data-fact-id="quality-methods" data-status="complete">{{ qualityMethods|join("、") }}</span>及其他品質管控方法。'),
}


def edit_source(name, source, language):
    operations = []
    def change(old, new, kind):
        assert source.count(old) == 1, (name, kind, source.count(old))
        start = source.index(old)
        operations.append(dict(start=start, end=start + len(old), before=old, after=new, kind=kind))
    def guard(old, condition, kind):
        change(old, '{% if ' + condition + ' %}' + old + '{% endif %}', kind)

    if name == 'src/quality-control.html.j2':
        start = source.index('  {% if qualityMethods %}')
        end = source.index('\n{% else %}\n', start)
        original = source[start:end]
        paragraph = ('<p class="quality-summary" data-fact-id="quality-other" data-status="partial">'
                     '{% if qualityMethods %}' + WORDS[language]['mixed'] + '{% else %}' +
                     WORDS[language]['other'] + '{% endif %}</p>')
        change(original, '{% if ' + SUBMIT + ' and ' + OTHER + ' %}' + paragraph +
               '{% else %}' + original + '{% endif %}', 'single-quality-summary')
    elif name == 'src/questions/01-how-data.html.j2':
        guard('<p>' + WORDS[language]['instruments'] + '</p>', REVIEW, 'missing-instruments')
    elif name == 'src/projects.html.j2':
        guard(source[source.index('<div id="dmp-projects">'):], 'projectsItems or ' + REVIEW, 'empty-project-overview')
        # Nested source edits cannot share offsets. Split the outer operation
        # into two zero-width insertions before adding the inner row operations.
        outer = operations.pop()
        operations += [dict(start=outer['start'], end=outer['start'], before='', after='{% if projectsItems or ' + REVIEW + ' %}', kind=outer['kind']),
                       dict(start=len(source.rstrip('\n')), end=len(source.rstrip('\n')), before='', after='{% endif %}', kind=outer['kind'])]
        for field in ['projectNumber', 'projectStart', 'projectEnd']:
            rows = [m[0] for m in re.finditer(r'<tr>.*?</tr>', source, re.S) if '{{ ' + field + ' ' in m[0]]
            assert len(rows) == 1
            guard(rows[0], field + ' or ' + REVIEW, 'missing-' + field)
        table_start = source.index('<table class="project-details">')
        table_end = source.index('</tbody></table>') + len('</tbody></table>')
        condition = 'projectNumber or projectStart or projectEnd or fundersItems or ' + REVIEW
        operations += [dict(start=table_start, end=table_start, before='', after='{% if ' + condition + ' %}', kind='empty-project-table'),
                       dict(start=table_end, end=table_end, before='', after='{% endif %}', kind='empty-project-table')]
        rows = list(re.finditer(r'<li>\{\{ macros.integrationCrossref\(funderNameReply\) \}\}.*?</li>', source, re.S))
        assert len(rows) == 1
        original = rows[0][0]
        status_start = original.index('{% if funderStatus')
        statuses = original[status_start:original.rindex('</li>')]
        separator = ': ' if language == 'english' else '：'
        new = ('<li>{% set funderLabel = macros.integrationCrossref(funderNameReply) %}{{ funderLabel }}'
               '{% if grantNumber %}{% if funderLabel|trim %}' + separator + '{% endif %}{{ grantNumber }}{% endif %} ' + statuses + '</li>')
        change(original, '{% if ' + SUBMIT + ' %}' + new + '{% else %}' + original + '{% endif %}', 'missing-grant-number')
    elif name == 'src/contributors.html.j2':
        original = source[source.index('<div id="dmp-contributors">'):].rstrip('\n')
        guard(original, 'contributorsItems or dc.project.created_by or ' + REVIEW, 'empty-contributor-overview')

    result = source
    ordered = sorted(operations, key=lambda o: (o['start'], o['end']))
    assert all(a['end'] <= b['start'] for a, b in zip(ordered, ordered[1:])), 'Overlapping source edits'
    for op in reversed(ordered):
        assert result[op['start']:op['end']] == op['before']
        result = result[:op['start']] + op['after'] + result[op['end']:]
    return result, ordered


def patch(data, language):
    marked, first = marked_patch(data, language)
    result = copy.deepcopy(marked); second = {}
    for file in result['files']:
        file['content'], edits = edit_source(file['fileName'], file['content'], language)
        if edits: second[file['fileName']] = edits
    assert reverse(reverse(result, second), first) == data
    return result, dict(marked=first, polish=second)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    manifest = json.loads((a.baseline / 'manifest.json').read_text())
    assert manifest['status'] == 'runtime-experiment' and manifest['runtime_variant']['name'] == 'python-markdown-tables'
    a.output.mkdir(parents=True)
    proof = dict(prototype_only=True, release_acceptance=False, global_switch_complete=False,
                 recipe_sha256=sha(Path(__file__)), packages={})
    for language in ['english', 'chinese']:
        name = language + '.zip'; assert sha(a.baseline / name) == BASE[name]
        with zipfile.ZipFile(a.baseline / name) as before, zipfile.ZipFile(a.output / name, 'w') as after:
            data, edits = patch(json.loads(before.read('template/template.json')), language)
            for entry in before.infolist():
                value = before.read(entry.filename)
                if entry.filename == 'template/template.json': value = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                after.writestr(entry, value)
        proof['packages'][name] = dict(baseline_sha256=BASE[name], sha256=sha(a.output / name), operations=edits)
        manifest['sha256'][name] = sha(a.output / name)
    manifest.pop('identical_package_sha256', None)
    manifest.update(prototype=proof, baseline_build=str(a.baseline.resolve()))
    for name, value in [('manifest.json', manifest), ('prototype.json', proof)]:
        (a.output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print(a.output)


if __name__ == '__main__': main()
