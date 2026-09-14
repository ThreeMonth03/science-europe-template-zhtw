"""Archive a bounded coverage experiment using checksum-bound reports and a size gate."""
import argparse
import json
import shutil
from pathlib import Path
from artifact_utils import sha

ROOT=Path(__file__).resolve().parents[1]
REPORTS=('preservation','sharing','polish','format','reading','quality')
PROBES=('preservation','sharing','format','reading','quality')


def read(root,name): return json.loads((root/name).read_text())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['baseline','variant','rebuild','english','destination','review-document','binding-audit']:
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--cases',nargs='+',required=True,help='Nonempty cases with provenance tables in both runtimes')
    args=parser.parse_args()
    assert not args.destination.exists(),'Never overwrite an earlier review'
    cases=set(args.cases)
    assert cases and len(cases)==len(args.cases) and 'structured' in cases and 'empty' not in cases
    compare=read(args.variant,'runtime-comparison.json')
    assert compare['selected_comparison_passed'] and compare['release_acceptance'] is False
    assert compare['checker_sha256']==sha(ROOT/'scripts/compare_runtime_outputs.py')
    assert {(r['case'],r['language']) for r in compare['checks']}=={(c,l) for c in cases for l in ['english','chinese']}
    packages=compare['package_sha256']; copies=[]
    def keep(source,name): copies.append((source,Path(name)))
    for side,root in [('stock',args.baseline),('tables',args.variant)]:
        manifest=read(root,'manifest.json'); pilot=read(root,'pilot-report.json')
        assert manifest['status']==('candidate' if side=='stock' else 'runtime-experiment')
        assert pilot['semantic_checks_passed'] and pilot['checker_sha256']==sha(ROOT/'scripts/run_pilot.py')
        chosen=cases|({'empty'} if side=='stock' else set())
        pairs={(c,l) for c in chosen for l in ['english','chinese']}
        render=read(root,'render-results.json')
        assert len(render)==len(pairs)*3 and all(r['passed'] for r in render)
        if side=='stock':
            assert not pilot['passed']
            assert {(r['case'],r['language'],r['code']) for r in pilot['blocking_issues']}=={(c,l,code) for c in cases for l in ['english','chinese'] for code in ['markdown-table-unsupported','docx-table-missing']}
            assert len(pilot['blocking_issues'])==len(cases)*4
        else: assert pilot['passed'] and not pilot['blocking_issues']
        for name,digest in packages.items(): assert sha(root/name)==digest==manifest['sha256'][name]==pilot['package_sha256'][name]
        for name,digest in compare['artifact_sha256'][side].items(): assert sha(root/name)==digest
        for kind in REPORTS:
            name=kind+'-report.json'; report=read(root,name)
            assert report['selected_checks_passed'] and report['release_acceptance'] is False
            assert report['checker_sha256']==sha(ROOT/f'scripts/check_{kind}_outputs.py')
            assert report['package_sha256']==packages
            assert {(r['case'],r['language']) for r in report['rows']}==pairs
            for path,digest in report.get('artifact_sha256',{}).items(): assert sha(root/path)==digest
            for path,digest in report.get('render_sha256',{}).items(): assert sha(root/'renders'/path)==digest
            for path,digest in report.get('helper_sha256',{}).items(): assert sha(ROOT/'scripts'/path)==digest
            if 'text_extractor_sha256' in report: assert report['text_extractor_sha256']==sha(ROOT/'scripts/check_narrative_outputs.py')
            if 'date_helper_sha256' in report: assert report['date_helper_sha256']==sha(ROOT/'scripts/check_polish_outputs.py')
            keep(root/name,f'{side}/{name}')
        for name in ['manifest.json','pilot-report.json','render-results.json']: keep(root/name,f'{side}/{name}')
        for case,lang in sorted({(c,'chinese') for c in chosen}|{('structured','english')}):
            for fmt in ['pdf','docx']:
                for suffix in ['', '.fixture.json']:
                    name=f'{case}-{lang}.{fmt}{suffix}'; keep(root/'renders'/name,f'{side}/{name}')
            if case!='empty':
                name=f'{case}-{lang}.pdf'; keep(root/'word-preview'/name,f'{side}/word-preview/{name}')
    for kind in PROBES:
        name=kind+'-translation-probe.json'; probe=read(args.baseline,name)
        assert probe['passed'] and probe['package_sha256']==packages
        assert probe['checker_sha256']==sha(ROOT/f'scripts/probe_{kind}_translation.py')
        if 'reviewed_phrases_sha256' in probe: assert probe['reviewed_phrases_sha256']==sha(ROOT/'docs/readability-phrases.json')
        keep(args.baseline/name,f'stock/{name}')
    audit=json.loads(args.binding_audit.read_text())
    assert not audit['source_dirty']
    assert all(not row['unbound_variables'] and not row['absent_entities'] for row in audit['templates'])
    assert audit['source_commit']==read(args.baseline,'manifest.json')['checkouts']['english']['commit']
    keep(args.binding_audit,'km-binding-audit.json')
    keep(args.english/'requirements/preservation-bindings-2.7.0.json','preservation-bindings-before.json')
    for name in ['translation-audit.json','structure-audit.json']: keep(args.baseline/name,f'stock/{name}')
    rebuild=read(args.rebuild,'manifest.json')
    assert rebuild['status']=='candidate' and all(not s['dirty'] for s in rebuild['checkouts'].values())
    for name,digest in packages.items(): assert sha(args.rebuild/name)==digest==rebuild['sha256'][name]
    keep(args.rebuild/'manifest.json','rebuild-manifest.json')
    keep(args.variant/'runtime-comparison.json','runtime-comparison.json')
    keep(args.review_document,'README.md')
    size=sum(source.stat().st_size for source,_ in copies)
    assert size<=25_000_000,(size,'Review exceeds size budget')
    assert len({name for _,name in copies})==len(copies),'Duplicate archive destination'
    args.destination.mkdir(parents=True,exist_ok=False)
    checksums={}
    for source,name in copies:
        target=args.destination/name; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target); checksums[str(name)]=sha(target)
    (args.destination/'checksums.json').write_text(json.dumps(checksums,indent=2)+'\n')
    print(json.dumps({'hashed_files':len(checksums),'bytes':size,'destination':str(args.destination)}))


if __name__=='__main__': main()
