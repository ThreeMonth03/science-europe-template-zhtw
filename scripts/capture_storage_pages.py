"""Render actual Q3 PDF/Word-preview pages for visual inspection, without cropping."""
import argparse
import json
from pathlib import Path
import subprocess
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_narrative_outputs import compact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['build', 'prior']: parser.add_argument('--'+name, type=Path, required=True)
    a = parser.parse_args(); out = a.build/'visual'; out.mkdir(exist_ok=True); records = []
    for label, folder in [('before', a.prior), ('after', a.build)]:
        for case in ['storage-missing', 'storage-partial', 'storage-zero', 'storage-complete']:
            for language in ['english', 'chinese']:
                stem = case+'-'+language
                soup = BeautifulSoup((folder/'renders'/(stem+'.html')).read_text(), 'html.parser')
                heading = compact(soup.select_one('#q-docs-metadata h3').get_text())
                for kind in ['pdf', 'word']:
                    pdf = folder/('renders' if kind == 'pdf' else 'word-preview')/(stem+'.pdf')
                    raw = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
                    pages = [compact(t) for t in raw.split('\f')[:-1]]
                    hits = [i for i, t in enumerate(pages, 1) if heading in t]; assert len(hits) == 1
                    number = hits[0]; target = out/(label+('-word-' if kind == 'word' else '-')+stem)
                    subprocess.run(['pdftoppm', '-f', str(number), '-l', str(number), '-scale-to', '1400',
                                    '-png', '-singlefile', str(pdf), str(target)], check=True, capture_output=True)
                    records.append({'source': str(pdf), 'source_sha256': sha(pdf), 'page': number,
                                    'total_pages': len(pages), 'image': target.name+'.png', 'image_sha256': sha(target.with_suffix('.png'))})
        for number in [3, 4]:
            pdf = folder/'renders/storage-partial-english.pdf'; target = out/(label+'-partial-english-page'+str(number))
            subprocess.run(['pdftoppm', '-f', str(number), '-l', str(number), '-scale-to', '1400',
                            '-png', '-singlefile', str(pdf), str(target)], check=True, capture_output=True)
            records.append({'source': str(pdf), 'source_sha256': sha(pdf), 'page': number,
                            'image': target.name+'.png', 'image_sha256': sha(target.with_suffix('.png'))})
    (out/'page-index.json').write_text(json.dumps(records, indent=2)+'\n')
    print(json.dumps({'captured_pages': len(records)}))


if __name__ == '__main__': main()
