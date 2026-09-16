"""Fresh LibreOffice previews bound to the native Word inputs; not MS Word QA."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from artifact_utils import sha
from check_word_short_budget_outputs import CASES


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True)
    p.add_argument('--cases',nargs='+',default=CASES);a=p.parse_args()
    out=a.build/'word-preview';out.mkdir(exist_ok=True)
    report={'release_acceptance':False,'microsoft_word_acceptance':False,'rows':[],
        'libreoffice':subprocess.check_output(['libreoffice','--version'],text=True).strip(),'checker_sha256':sha(Path(__file__))}
    target=a.build/('word-preview-'+('-'.join(a.cases))+'.json');assert not target.exists()
    try:
        for case in a.cases:
            for language in ['english','chinese']:
                name=case+'-'+language;source=a.build/'renders'/(name+'.docx');destination=out/(name+'.pdf')
                assert source.is_file() and not destination.exists()
                with tempfile.TemporaryDirectory(prefix='se-word-short-lo-') as folder:
                    result=subprocess.run(['libreoffice','-env:UserInstallation='+Path(folder).as_uri(),'--headless','--convert-to','pdf','--outdir',str(out),str(source)],capture_output=True,text=True)
                assert result.returncode==0 and destination.is_file(),result.stderr
                report['rows'].append({'name':name,'docx_sha256':sha(source),'preview_sha256':sha(destination)})
                print(name,flush=True)
        report['completed']=True
    finally:target.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
