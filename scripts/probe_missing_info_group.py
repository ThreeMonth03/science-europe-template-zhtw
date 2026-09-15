"""Check actual worker CSS for the bounded empty-Q15 group and long-answer controls."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from bs4 import BeautifulSoup
from artifact_utils import sha

RUNNER = '''import json,sys,re
from weasyprint import HTML,__version__
payload=json.load(sys.stdin); results=[]
compact=lambda s:re.sub(r'\\s+', '', s)
for row in payload['cases']:
    document=HTML(string='<style>'+payload['css']+'</style><div style="height:205mm">Before the group.</div>'+row['html']).render()
    boxes=[box for page in document.pages for box in page._page_box.descendants()
           if type(box).__name__=='BlockBox' and box.element.get('id')=='q-required-resources']
    assert boxes and {box.style['break_inside'] for box in boxes}=={row['expected']}, row['case']
    pages=[compact(''.join(b.text for b in page._page_box.descendants() if type(b).__name__=='TextBox')) for page in document.pages]
    if row['expected']=='avoid':
        hits=[[i+1 for i,page in enumerate(pages) if compact(text) in page] for text in row['texts']]
        assert all(len(h)==1 for h in hits) and len({h[0] for h in hits})==1, (row['case'],hits)
    results.append({'case':row['case'],'computed_break_inside':row['expected'],'pages':len(pages),'passed':True})
print(json.dumps({'weasyprint':__version__,'rows':results}))
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True); p.add_argument('--english', type=Path, required=True); a = p.parse_args()
    sys.path.insert(0, str(a.english.resolve()/'scripts'))
    from probe_pdf_budget_reading import render
    from probe_budget_word import IMAGE
    rows = []
    for folder in ['en', 'translated']:
        original = render(a.build/folder, {}, True)
        soup = BeautifulSoup(original, 'html.parser')
        texts = [n.get_text() for n in soup.select('h3, .data-gap')]; assert len(texts) == 5
        cases = [('empty', original, 'avoid'),
                 ('wrong-fact', original.replace('hardware-software', 'unknown-fact'), 'auto'),
                 ('authored-detail', original.replace('<div class="answer">', '<div class="answer"><p>Original author detail.</p>'), 'auto'),
                 ('long-answer', original.replace('<div class="answer">', '<div class="answer">'+'<p>Original long answer.</p>'*60), 'auto')]
        payload = {'css': (a.build/folder/'src/layout.css').read_text(), 'cases': [
            {'case': folder+'/'+name, 'html': html, 'expected': expected, 'texts': texts} for name, html, expected in cases]}
        result = json.loads(subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '-i', '--entrypoint', 'python', IMAGE,
            '-c', RUNNER], input=json.dumps(payload).encode()))
        rows.extend(result['rows'])
    report = {'passed': True, 'release_acceptance': False, 'rows': rows, 'checker_sha256': sha(Path(__file__)),
              'worker_image': IMAGE, 'package_sha256': {n: sha(a.build/n) for n in ['english.zip', 'chinese.zip']},
              'limits': ['Selected real template fragments and pinned CSS engine, not a full native DSW export']}
    target = a.build/'missing-info-group-probe.json'; assert not target.exists()
    target.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'passed': True, 'cases': len(rows)}))


if __name__ == '__main__': main()
