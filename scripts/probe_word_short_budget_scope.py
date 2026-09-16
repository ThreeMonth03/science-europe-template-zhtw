"""0.3.26 vs frozen 0.3.25: four bounded Word-hint source edits, no translation edits."""
import argparse
import hashlib
import json
from pathlib import Path
from artifact_utils import sha
from probe_q8_word_scope import verify_translations

ROOT=Path(__file__).resolve().parents[1]
FILES=['src/budget-reading.html.j2','src/questions/15-required-resources.html.j2','src/word/index.html.j2','src/word/pilot.lua']
WORD_BRANCH='''                    {%- elif word_budget_reading|default(false) -%}
                      {%- import 'src/budget-reading.html.j2' as budgetReading -%}
                      {{ budgetReading.short_table(originalBudgetTable, budgetLayout.rows, true) }}
'''
HELPER_BRANCH='''    {%- if word -%}
      {{- original|replace('<table class="resource-table">', '<table class="resource-table word-short-budget">'|safe, 1) -}}
    {%- else -%}
      {{- original|replace('<table class="resource-table">', '<table class="resource-table pdf-short-budget">'|safe, 1) -}}
    {%- endif -%}'''


def remove_once(source,old,new=''):
    assert source.count(old)==1,'Expected one exact reviewed insertion'
    return source.replace(old,new,1)


def restore(name,source):
    if name=='src/word/index.html.j2':return remove_once(source,'{%- set word_budget_reading = true -%}\n')
    if name=='src/questions/15-required-resources.html.j2':return remove_once(source,WORD_BRANCH)
    if name=='src/budget-reading.html.j2':
        source=remove_once(source,'macro short_table(original, rows, word=false)','macro short_table(original, rows)')
        source=remove_once(source,'An output-specific hint','A PDF-only hint')
        return remove_once(source,HELPER_BRANCH,'    '+HELPER_BRANCH.splitlines()[3].lstrip())
    assert name=='src/word/pilot.lua'
    start='-- BEGIN short-budget Word columns\n';end='-- END short-budget Word columns\n\n'
    assert source.count(start)==source.count(end)==1
    before,rest=source.split(start);_,after=rest.split(end)
    return remove_once(before+after,'  if div.identifier == "q-required-resources" then div = widen_short_budget_columns(div) end\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);a=p.parse_args()
    prior=ROOT/'reviews/2026-09-16-short-budget-reading'
    old=json.loads((prior/'candidate-manifest.json').read_text());new=json.loads((a.build/'manifest.json').read_text())
    verify_translations(old,new);rows=[]
    for row in json.loads((prior/'probes/short-budget-scope.json').read_text())['rows']:
        folder=a.build/row['language'];before=row['after']
        after={str(f.relative_to(folder)):sha(f) for f in (folder/'src').rglob('*') if f.is_file()}
        assert before.keys()==after.keys()
        changed=sorted(n for n in before if before[n]!=after[n]);assert changed==FILES,(row['language'],changed)
        for name in changed:
            restored=restore(name,(folder/name).read_text())
            assert hashlib.sha256(restored.encode()).hexdigest()==before[name],(row['language'],name,'Unreviewed source edit')
        rows.append({'language':row['language'],'changed':changed,'before':before,'after':after})
    report={'passed':True,'release_acceptance':False,'unchanged_translation_files':731,'rows':rows,
        'checker_sha256':sha(Path(__file__)),'prior_manifest_sha256':sha(prior/'candidate-manifest.json'),
        'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']}}
    target=a.build/'word-short-budget-scope.json';assert not target.exists();target.write_text(json.dumps(report,indent=2)+'\n')
    print('Word short-budget scope passed: 731 translations exact; four bounded source changes.')


if __name__=='__main__':main()
