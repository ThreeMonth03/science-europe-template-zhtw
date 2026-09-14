"""Archive the bounded 0.3.8 style experiment after hash, scope and size gates."""
import argparse
import json
import shutil
import zipfile
from pathlib import Path
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]
STOCK = {'preservation-complete','structured','empty'}
TABLES = {'preservation-complete','preservation-partial','preservation-custom','structured','narrative-long','table-long'}
REPORTS = ['preservation','sharing','polish','format','reading','quality','word-rhythm']


def read(root, name): return json.loads((root/name).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['baseline','variant','prior-stock','prior-tables','rebuild','destination','review-document','english','rehearsal']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    assert not args.destination.exists(), 'Never overwrite a review'
    packages = {n: sha(args.baseline/n) for n in ['english.zip','chinese.zip']}
    copies = []
    def keep(source, name): copies.append((source,Path(name)))
    comparison = read(args.variant,'runtime-comparison.json')
    common = (STOCK & TABLES)
    assert comparison['selected_comparison_passed'] and comparison['release_acceptance'] is False
    assert comparison['package_sha256'] == packages
    assert comparison['checker_sha256'] == sha(ROOT/'scripts/compare_runtime_outputs.py')
    assert {(r['case'],r['language']) for r in comparison['checks']} == {(c,l) for c in common for l in ['english','chinese']}
    for side, root, prior, cases in [('stock',args.baseline,args.prior_stock,STOCK),('tables',args.variant,args.prior_tables,TABLES)]:
        pairs = {(c,l) for c in cases for l in ['english','chinese']}
        manifest = read(root,'manifest.json'); pilot = read(root,'pilot-report.json'); renders = read(root,'render-results.json')
        assert manifest['status'] == ('candidate' if side == 'stock' else 'runtime-experiment')
        assert pilot['semantic_checks_passed'] and pilot['checker_sha256'] == sha(ROOT/'scripts/run_pilot.py')
        assert len(renders) == len(pairs)*3 and all(r['passed'] for r in renders)
        if side == 'stock':
            expected = {(c,l,code) for c,l in pairs if c!='empty' for code in ['markdown-table-unsupported','docx-table-missing']}
            assert not pilot['passed'] and len(pilot['blocking_issues']) == len(expected)
            assert {(r['case'],r['language'],r['code']) for r in pilot['blocking_issues']} == expected
        else: assert pilot['passed'] and not pilot['blocking_issues']
        for n,d in packages.items(): assert d == sha(root/n) == manifest['sha256'][n] == pilot['package_sha256'][n]
        for path,digest in comparison['artifact_sha256'][side].items(): assert sha(root/path) == digest
        for kind in REPORTS:
            name = kind+'-report.json'; report = read(root,name)
            assert report['selected_checks_passed'] and report['release_acceptance'] is False
            assert report['package_sha256'] == packages
            assert report['checker_sha256'] == sha(ROOT/f'scripts/check_{kind.replace("-","_")}_outputs.py')
            assert len(report['rows'])==len(pairs) and {(r['case'],r['language']) for r in report['rows']} == pairs
            for path,digest in report.get('artifact_sha256',{}).items(): assert sha(root/path) == digest
            for path,digest in report.get('render_sha256',{}).items(): assert sha(root/'renders'/path) == digest
            for path,digest in report.get('helper_sha256',{}).items(): assert sha(ROOT/'scripts'/path) == digest
            for key,path in [('text_extractor_sha256','check_narrative_outputs.py'),('date_helper_sha256','check_polish_outputs.py')]:
                if key in report: assert report[key] == sha(ROOT/'scripts'/path)
            if kind == 'word-rhythm':
                assert report['prior_package_sha256'] == {n:sha(prior/n) for n in packages}
                for path,digest in report['prior_artifact_sha256'].items(): assert sha(prior/path) == digest
                assert sum(r['question_comparisons'] for r in report['rows']) == (90 if side=='stock' else 120)
                assert set(report['uncompared_cases']) == (set() if side=='stock' else {'narrative-long','table-long'})
            keep(root/name,f'{side}/{name}')
        for name in ['manifest.json','pilot-report.json','render-results.json']: keep(root/name,f'{side}/{name}')
        for case,lang in sorted(pairs):
            for fmt in ['pdf','docx']:
                for extra in ['', '.fixture.json']:
                    name=f'{case}-{lang}.{fmt}{extra}'; keep(root/'renders'/name,f'{side}/{name}')
            name=f'{case}-{lang}.pdf'; keep(root/'word-preview'/name,f'{side}/word-preview/{name}')
    for kind in ['preservation','sharing','format','reading','quality']:
        name=kind+'-translation-probe.json'; probe=read(args.baseline,name)
        assert probe['passed'] and probe['package_sha256']==packages
        assert probe['checker_sha256']==sha(ROOT/f'scripts/probe_{kind}_translation.py')
        keep(args.baseline/name,f'stock/{name}')
    for name in ['translation-audit.json','structure-audit.json']:
        assert read(args.baseline,name)==[]; keep(args.baseline/name,f'stock/{name}')
    audit=read(args.baseline,'selection-scope-report.json')
    assert not audit['source_dirty'] and audit['source_commit']==read(args.baseline,'manifest.json')['checkouts']['english']['commit']
    assert audit['checker_sha256']==sha(ROOT/'scripts/audit_selection_scope.py')
    for path,digest in audit['template_sha256'].items(): assert sha(args.english/path)==digest
    keep(args.baseline/'selection-scope-report.json','selection-scope-report.json')
    keep(args.english/'docs/selection-policy-review.md','selection-policy-review.md')
    rebuild=read(args.rebuild,'manifest.json')
    assert rebuild['status']=='candidate' and all(not s['dirty'] for s in rebuild['checkouts'].values())
    assert {n:sha(args.rebuild/n) for n in packages}==packages
    keep(args.rebuild/'manifest.json','rebuild-manifest.json')
    keep(args.variant/'runtime-comparison.json','runtime-comparison.json')
    keep(args.review_document,'README.md')
    rehearsal=read(args.rehearsal,'report.json')
    original=args.prior_stock/'renders/preservation-complete-chinese.docx'
    assert rehearsal['source_sha256']==sha(original) and rehearsal['release_acceptance'] is False
    assert set(rehearsal['variants'])=={'line-only','rhythm'}
    with zipfile.ZipFile(original) as archive:
        original_parts={n:archive.read(n) for n in archive.namelist()}
    for profile,row in rehearsal['variants'].items():
        docx=args.rehearsal/(profile+'.docx')
        assert row['sha256']==sha(docx) and row['all_non_style_parts_byte_identical']
        with zipfile.ZipFile(docx) as archive:
            assert set(archive.namelist())==set(original_parts)
            assert all(archive.read(n)==data for n,data in original_parts.items() if n!='word/styles.xml')
        for suffix in ['docx','pdf']: keep(args.rehearsal/(profile+'.'+suffix),'rehearsal/'+profile+'.'+suffix)
    keep(args.rehearsal/'report.json','rehearsal/report.json')
    # Bind every package source file, not just a visual assertion about similarity.
    delta={}
    for side in ['en','translated']:
        a,b=[{str(p.relative_to(r/side)):sha(p) for p in sorted((r/side/'src').rglob('*')) if p.is_file()} for r in [args.prior_stock,args.baseline]]
        assert a.keys()==b.keys()
        changes=[p for p in a if a[p]!=b[p]]
        assert changes==['src/word/reference.docx'],(side,changes)
        delta[side]={'changed_source_paths':changes,'prior_source_sha256':a,'source_sha256':b}
    size=sum(p.stat().st_size for p,_ in copies)
    delta_bytes=(json.dumps(delta,indent=2)+'\n').encode()
    assert size+len(delta_bytes)<=25_000_000, 'Review exceeds size budget'
    assert len({n for _,n in copies})==len(copies)
    args.destination.mkdir(parents=True,exist_ok=False); hashes={}
    for source,name in copies:
        target=args.destination/name; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target); hashes[str(name)]=sha(target)
    target=args.destination/'style-source-delta.json'; target.write_bytes(delta_bytes); hashes[target.name]=sha(target)
    (args.destination/'checksums.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print(json.dumps({'hashed_files':len(hashes),'bytes':size+len(delta_bytes),'destination':str(args.destination)}))


if __name__=='__main__': main()
