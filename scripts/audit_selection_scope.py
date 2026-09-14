"""Bind a bounded selection-policy review to a cached compiled public KM inventory."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from jinja2 import Environment, nodes

PATTERN = r'preserv|retai|reten|discard|destroy|destruct|select|sustain|policy|policies|archiv|long.term'


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--english', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Do not overwrite a review'
    inventory = json.loads(args.inventory.read_text())
    km = inventory['knowledge_models']
    for language, filename in [('en','root-2.7.0.km'),('zh-Hant','root-zh-hant-2.7.0.km')]:
        assert km[language]['km_sha256'] == digest(args.english/'fixtures/knowledge-models'/filename)
    ids = dict(re.findall(r'set\s+(\w+)\s*=\s*"([0-9a-f-]{36})"', (args.english/'src/uuids.j2').read_text()))
    references = {}; env = Environment(extensions=['jinja2.ext.do'])
    for path in sorted((args.english/'src').rglob('*.j2')):
        for node in env.parse(path.read_text()).find_all(nodes.Getattr):
            if isinstance(node.node,nodes.Name) and node.node.name == 'uuids' and node.attr in ids:
                references.setdefault(ids[node.attr],set()).add(str(path.relative_to(args.english)))
    pattern = re.compile(PATTERN,re.I)
    selected = [r['uuid'] for r in km['en']['questions'] if pattern.search(r['title']+' '+str(r.get('guidance'))+' '+' '.join(c['label'] for c in r['choices']+r['multi_choices']))]
    candidates = {}
    for language in ['en','zh-Hant']:
        indexed = {r['uuid']: r for r in km[language]['questions']}
        candidates[language] = []
        for uid in selected:
            row = dict(indexed[uid])
            row['bindings'] = sorted(n for n,v in ids.items() if v == uid)
            row['static_template_references'] = sorted(references.get(uid,[]))
            candidates[language].append(row)
    state = subprocess.check_output(['git','-C',str(args.english),'status','--porcelain'],text=True)
    assert not state, 'Review source must be clean'
    report = {'source_commit': subprocess.check_output(['git','-C',str(args.english),'rev-parse','HEAD'],text=True).strip(),
              'source_dirty': False, 'release_acceptance': False, 'source_inventory_sha256': digest(args.inventory),
              'compiled_inventory_source_commit': inventory['source_commit'],
              'km_sha256': {lang: km[lang]['km_sha256'] for lang in candidates},
              'checker_sha256': digest(Path(__file__)), 'search_pattern': PATTERN,
              'template_sha256': {str(p.relative_to(args.english)): digest(p) for p in sorted((args.english/'src').rglob('*.j2'))},
              'reachable_question_counts': {lang: km[lang]['reachable_question_count'] for lang in candidates},
              'candidate_count': len(selected), 'candidates': candidates,
              'limits': ['Keyword candidates are not an exhaustive semantic audit or absence proof', 'Static references are not runtime branch coverage', 'No production project answers', 'No new KM fields or runtime answers are created']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'candidate_count': len(selected), 'languages': list(candidates)}))


if __name__ == '__main__': main()
