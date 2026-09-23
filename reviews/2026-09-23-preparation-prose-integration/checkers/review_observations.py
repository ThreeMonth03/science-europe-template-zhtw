"""Confirm selected visual observations with synthetic document text only."""
import hashlib,json,subprocess
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent
def text(path,page):
    return subprocess.check_output(['pdftotext','-f',str(page),'-l',str(page),str(path),'-'],text=True)
def compact(value):return ''.join(value.split())
def main():
    en=ROOT/'candidate/renders/POSITIVE-en-submission'
    wording='metadata and we will use the following metadata standards:'
    assert wording in BeautifulSoup((en/'document.html').read_text(),'html.parser').get_text(' ',strip=True)
    assert compact(wording) in compact(text(en/'document.pdf',2))
    rows=[]
    for arm in ['baseline','candidate']:
        folder=ROOT/arm/'renders/MISSING-zh-Hant-submission'
        soup=BeautifulSoup((folder/'document.html').read_text(),'html.parser')
        heading=soup.select_one('#q-required-resources > h3')
        assert heading is not None
        title=compact(heading.get_text())
        pdf=folder/'word-preview/document.pdf'
        page2,page3=[compact(text(pdf,p)) for p in [2,3]]
        assert title not in page2 and title in page3
        # The last page contains only the Q15 title plus its page-number footer.
        assert page3==title+'3/3'
        rows.append(dict(arm=arm,case='MISSING',language='zh-Hant',profile='submission',
            format='libreoffice-word-preview',question_15_alone_on_last_page=True,pages=3))
    report=dict(scope='Observation verification; not a release acceptance test',
        english_conjunction_present_in_html_and_pdf=True,
        suspected_english_conjunction_loss_rejected=True,
        known_word_pagination_issue=rows,production_changed=False)
    with (ROOT/'observation-checks.json').open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps(report))
if __name__=='__main__':main()
