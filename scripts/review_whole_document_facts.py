"""Record narrow, reproducible observations without turning audit findings into acceptance."""
import argparse
import json
from pathlib import Path
import subprocess
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_narrative_outputs import page_bounds
from check_word_rhythm_outputs import inspect_preview


def compact(text):
    return ''.join(text.split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True)
    args = parser.parse_args()
    target = args.review / 'observations.json'
    assert not target.exists()
    inventory = json.loads((args.review / 'inventory.json').read_text())
    observations = []
    for row in inventory['rows']:
        stem = row['case'] + '-' + row['language']
        soup = BeautifulSoup((args.review / 'question-content' / (stem + '.html')).read_text(), 'html.parser')
        inputs = {name: q for q in row['selected_input_questions'] for name in q['bindings']}
        q6 = soup.select_one('#q-access-security .answer')
        q8 = soup.select_one('#q-copyright-ipr .answer')
        parent = inputs['sharedWorkspaceQUuid']
        selected = next(c for c in parent['choices'] if c['uuid'] == parent['fixture_reply']['value'])
        assert inputs['sharedAccessControlQUuid']['uuid'] in selected['follow_up_uuids']
        assert inputs['sharedAccessControlQUuid']['fixture_reply'] is None
        assert inputs['ownershipQUuid']['fixture_reply'] is None
        observations.append({'case': row['case'], 'language': row['language'],
            'q6_active_access_control_followup_missing': True,
            'q6_missing_or_review_marker_count': len(q6.select('[data-status="missing"], [data-status="missing-output"], .data-gap, .data-review')),
            'q8_ownership_reply_missing': True,
            'q8_missing_or_review_marker_count': len(q8.select('[data-status="missing"], [data-status="missing-output"], .data-gap, .data-review')),
            'q6_rendered_text': q6.get_text(' ', strip=True), 'q8_rendered_text': q8.get_text(' ', strip=True),
            'formats': {}})
        for fmt, original in row['formats'].items():
            pdf = args.review / ('native' if fmt == 'pdf' else 'word-preview') / (stem + '.pdf')
            assert sha(pdf) == original['sha256']
            pages = (page_bounds if fmt == 'pdf' else inspect_preview)(pdf)
            assert pages == original['pages']
            texts = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True).split('\f')[:-1]
            sections = []
            for section in soup.select('.dmp-section'):
                heading = section.h2.get_text(' ', strip=True)
                matches = [i for i, text in enumerate(texts, 1) if compact(heading) in compact(text)]
                assert len(matches) == 1
                question = section.select_one('.question')['id']
                sections.append({'id': section['id'], 'heading_page': matches[0],
                    'first_question_page': original['question_heading_pages'][question],
                    'separated_from_first_question': matches[0] != original['question_heading_pages'][question]})
            budget_heading = 'Data-management budget' if row['language'] == 'english' else '資料管理預算'
            budget_pages = [i for i, text in enumerate(texts, 1) if compact(budget_heading) in compact(text)]
            assert len(budget_pages) == 1
            observations[-1]['formats'][fmt] = {'pages': pages, 'word_boxes_within_page': True,
                'within_text_block_line_overlap_checked': fmt == 'word-preview',
                'sections': sections, 'budget_heading_page': budget_pages[0],
                'q15_heading_page': original['question_heading_pages']['q-required-resources']}
    report = {'release_acceptance': False, 'checker_sha256': sha(Path(__file__)),
              'inventory_sha256': sha(args.review / 'inventory.json'), 'rows': observations,
              'limits': ['Missing markers are an observed defect, not a passed completeness gate',
                         'Page bounds and within-block checks do not prove no overlap across blocks',
                         'A budget heading on another page is evidence for manual review, not automatically an error',
                         'No Microsoft Word or deployment-worker acceptance']}
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'documents': len(observations), 'section_orphans':
        sum(s['separated_from_first_question'] for r in observations for f in r['formats'].values() for s in f['sections'])}))


if __name__ == '__main__':
    main()
