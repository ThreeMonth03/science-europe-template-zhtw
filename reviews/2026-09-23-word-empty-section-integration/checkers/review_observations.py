"""Check whether a page-end real-snapshot question lost an answer (no public text)."""
import json, subprocess
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent
def compact(text):return ''.join(text.split())
def main():
    questions=[]
    for arm in ['baseline','candidate']:
        folder=ROOT/arm/'renders/P19-zh-Hant-submission'
        soup=BeautifulSoup((folder/'document.html').read_bytes(),'html.parser')
        metadata=soup.select_one('#q-docs-metadata').get_text()
        phrase='由所使用的資料儲存庫管理'; end=metadata.index(phrase)+len(phrase)
        assert metadata[end:end+2]=='）。', 'Unexpected literal space between fixed closing punctuation'
        q=soup.select_one('#q-quality-control');assert q is not None
        assert 'compact-empty-question' in q.get('class',[])
        answer=q.select_one('.answer');assert answer is not None and not answer.get_text(strip=True)
        title=compact(q.select_one('h3').get_text())
        second=compact(subprocess.check_output(['pdftotext','-f','2','-l','2',str(folder/'document.pdf'),'-'],text=True))
        third=compact(subprocess.check_output(['pdftotext','-f','3','-l','3',str(folder/'document.pdf'),'-'],text=True))
        section=compact(soup.select_one('#sec-storage-backup > h2').get_text())
        assert title in second and section in third and section not in second
        questions.append(str(q))
    assert questions[0]==questions[1]
    result=dict(passed=True,case='REAL-SNAPSHOT-A',language='zh-Hant',profile='submission',
        page_end_question=4,question_is_unanswered=True,answer_visible_text_empty=True,
        original_question_kept=True,next_section_starts_on_following_page=True,
        suspected_answer_separation_rejected=True,baseline_and_candidate_question_identical=True,
        fixed_parenthesis_period_have_no_literal_whitespace=True,
        interpretation='An intentionally retained empty question, not a lost answer or a new integration regression')
    with (ROOT/'observation-checks.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(passed=True,suspected_answer_separation_rejected=True)))
if __name__=='__main__':main()
