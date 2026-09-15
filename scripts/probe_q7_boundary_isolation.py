"""Prove the final paragraph repair is isolated; do not relabel earlier native packages."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from artifact_utils import sha

QUESTION = 'src/questions/07-personal-data.html.j2'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'english']: p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); sys.path.insert(0, str(a.english.resolve()/'tests')); sys.path.insert(0, str(a.english.resolve()/'scripts'))
    import test_science_europe_contract as adapter
    from generate_missing_info_fixtures import missing_info_cases
    rows = []; package_diffs = []
    for language, folder, locale in [('english', 'en', 'en'), ('chinese', 'translated', 'zh-Hant')]:
        packages = []
        for root in [a.before, a.after]:
            with zipfile.ZipFile(root/(language+'.zip')) as z:
                packages.append({name: z.read(name) for name in z.namelist()})
        left, right = packages; assert set(left) == set(right)
        assert [n for n in left if left[n] != right[n]] == ['template/template.json']
        left, right = [json.loads(d['template/template.json']) for d in packages]
        assert {n for n in left if left[n] != right[n]} == {'createdAt', 'updatedAt', 'files'}
        left_files, right_files = [{f['fileName']: f for f in d['files']} for d in [left, right]]
        assert set(left_files) == set(right_files)
        assert [n for n in left_files if left_files[n] != right_files[n]] == [QUESTION]
        package_diffs.append({'language': language, 'only_changed_template_file': QUESTION,
                              'before_sha256': sha(a.before/(language+'.zip')), 'after_sha256': sha(a.after/(language+'.zip'))})
        templates = []
        for root, files in [(a.before, left_files), (a.after, right_files)]:
            source = root/folder/QUESTION
            assert files[QUESTION]['content'] == source.read_text()
            env = Environment(loader=FileSystemLoader(root/folder), extensions=['jinja2.ext.do'])
            env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items, reply_str_value=adapter.reply_str_value, markdown=lambda v: v)
            templates.append(env.from_string("{% import 'src/uuids.j2' as uuids %}{% include '"+QUESTION+"' %}"))
        for name, raw in missing_info_cases(locale).items():
            replies = {p: v['value'] for p, v in raw.items()}
            old, new = [t.render(repliesMap=replies) for t in templates]
            if name != 'personal-data-partial': assert old == new, (name, language, 'Unrelated fixture output changed')
            current = BeautifulSoup(new, 'html.parser'); assert not current.select('p p, p div, p ul, p table')
            rows.append({'case': name, 'language': language, 'q7_output_byte_identical': old == new,
                         'requires_fresh_native_q7_validation': name == 'personal-data-partial'})
    report = {'passed': True, 'release_acceptance': False, 'rows': rows, 'package_diffs': package_diffs,
              'checker_sha256': sha(Path(__file__)), 'limits': ['Unchanged source and selected branch outputs, not a re-export of every final ZIP case',
                  'The repaired Q7 case must be natively re-rendered in both languages; old failure is retained']}
    target = a.after/'q7-boundary-isolation-proof.json'; assert not target.exists()
    target.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'passed': True, 'unchanged_branch_outputs': sum(r['q7_output_byte_identical'] for r in rows)}))


if __name__ == '__main__': main()
