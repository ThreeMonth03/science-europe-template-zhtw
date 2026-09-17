"""Record Q5 context reflow after Q3 additions; no claim of full visual acceptance."""
import argparse
import json
from pathlib import Path
import subprocess
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_narrative_outputs import compact
from check_metadata_followup_outputs import CASES


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ['build','prior']: p.add_argument('--'+n,type=Path,required=True)
    a = p.parse_args(); out = a.build/'diagnostics'; out.mkdir(exist_ok=True)
    target = out/'q5-context-reflow.json'; assert not target.exists()
    rows, captures = [], []
    for case in CASES:
        for language in ['english','chinese']:
            stem = case+'-'+language
            for kind in ['pdf','word']:
                row = dict(case=case,language=language,format=kind)
                for label, root in [('before',a.prior),('after',a.build)]:
                    soup = BeautifulSoup((root/'renders'/(stem+'.html')).read_text(),'html.parser')
                    q = soup.select_one('#q-store-backup')
                    facts = [('heading',q.h3),('policy',q.select_one('.workspace-policy')),
                             ('limitations-intro',q.select_one('.storage-detail-limits p'))]
                    facts += [(n['data-fact-id'],n) for n in q.select('.storage-detail-limits li')]
                    pdf = root/('renders' if kind=='pdf' else 'word-preview')/(stem+'.pdf')
                    pages = [compact(t) for t in subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True).split('\f')[:-1]]
                    found = {key:[i for i,text in enumerate(pages,1) if compact(node.get_text()) in text]
                             for key,node in facts if node is not None}
                    assert all(len(value)==1 for value in found.values()), found
                    row[label] = dict(pdf_sha256=sha(pdf),locations=found,
                                      together=len({v[0] for v in found.values()})==1)
                row['new_separation'] = row['before']['together'] and not row['after']['together']
                rows.append(row)
                if row['new_separation']:
                    for label,root in [('before',a.prior),('after',a.build)]:
                        pdf = root/('renders' if kind=='pdf' else 'word-preview')/(stem+'.pdf')
                        for number in sorted({v[0] for v in row[label]['locations'].values()}):
                            image = out/(label+'-'+kind+'-'+stem+'-q5-page'+str(number))
                            subprocess.run(['pdftoppm','-f',str(number),'-l',str(number),'-scale-to','1400',
                                            '-png','-singlefile',str(pdf),str(image)],check=True,capture_output=True)
                            captures.append(dict(image=image.name+'.png',image_sha256=sha(image.with_suffix('.png')),
                                                 pdf_sha256=sha(pdf),page=number))
    report = dict(measurement_completed=True,release_acceptance=False,checker_sha256=sha(Path(__file__)),
                  new_separations=sum(r['new_separation'] for r in rows),rows=rows,captures=captures,
                  next_action='Separate bounded Q5 context/limitation pagination fix; do not globally forbid page breaks or reduce font sizes.')
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'new_separations':report['new_separations'],'cases':[
        [r['case'],r['language'],r['format']] for r in rows if r['new_separation']]}))


if __name__=='__main__': main()
