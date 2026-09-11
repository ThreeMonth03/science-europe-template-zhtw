"""Local Jinja branch probes on the prepared EN and translated ZH source.

Uses the English unit-test reply adapter, not the DSW worker. Complementary to,
not a replacement for, end-to-end rendering of the broader fixture cases.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--english', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.english.resolve() / 'tests'))
    import test_science_europe_contract as harness
    ids = dict(re.findall(r'set\s+(\w+)\s*=\s*"([0-9a-f-]{36})"', (args.english / 'src/uuids.j2').read_text()))

    def path(*parts):
        return '.'.join(ids.get(part, part) for part in parts)

    projects = path('adminDetailsCUuid', 'projectsQUuid')
    approval = path(projects, 'p1', 'projEthicalApprovalQUuid')
    records = path(approval, 'projEthicalApprovalYesAUuid', 'projEthicalApprovalAuthQUuid')
    replies = {projects: ['p1'], approval: ids['projEthicalApprovalYesAUuid'], records: ['planned', 'applied', 'granted', 'rejected', 'missing']}
    for name, binding in [('planned', 'Planned'), ('applied', 'Applied'), ('granted', 'Granted'), ('rejected', 'Reject')]:
        replies[path(records, name, 'projEthicalApprovalAuthStatusQUuid')] = ids[f'projEthicalApprovalAuthStatus{binding}AUuid']
    replies[path(records, 'missing', 'projEthicalApprovalAuthCaseQUuid')] = 'CASE-2026-B<&>'
    expected = {'english': ['Approval is planned.', 'An application for approval has been submitted.', 'Approval has been granted.', 'Approval has been rejected.', 'Approval status has not been provided.'],
                'chinese': ['預計申請倫理審查。', '已提出倫理審查申請。', '倫理審查已核准。', '倫理審查未獲核准。', '尚待補充：倫理審查進度。']}
    checks = []
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        harness.ROOT = args.build / folder
        result = harness.render_question('src/questions/09-ethical-issues.html.j2', replies)
        assert all(needle in result for needle in expected[language]), language
        assert result.count('class="ethical-project"') == 1, language
        assert 'CASE-2026-B&lt;&amp;&gt;' in result, 'Case ID must be escaped, not altered'
        (args.build / f'ethical-branches-{language}.html').write_text(result)
        checks.append({'language': language, 'four_statuses_and_missing_status': True, 'one_unnamed_project': True, 'case_identifier_escaped': True})
    report = {'checks': checks, 'release_acceptance': False, 'runtime_render': False,
              'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (args.build / 'translated-branch-probe.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
