"""Separate mechanical preservation success from failed pagination acceptance."""
import json
import check

def main():
    mechanical=check.read(check.ROOT/'checks.json')
    assert mechanical['passed'] and len(mechanical['rows'])==28
    regressions=[];improvements=[]
    for row in mechanical['rows']:
        for kind,counts in row['pages'].items():
            value=dict(case=row['case'],locale=row['locale'],profile=row['profile'],format=kind,**counts)
            if counts['after']>counts['before']:regressions.append(value)
            if counts['after']<counts['before']:improvements.append(value)
    q8=check.read(check.ROOT/'q8-boundaries.json')
    assert len(q8['rows'])==16
    result=dict(passed=not regressions,release_acceptance=False,source_integration_blocked=bool(regressions),
        mechanical_preservation_passed=True,page_regressions=regressions,page_improvements=improvements,
        q8_split_boundaries=[r for r in q8['rows'] if not r['label_kept_with_permission']],
        all_candidate_pages_visually_inspected=False,native_ms_word=False)
    with (check.ROOT/'layout-gate.json').open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
