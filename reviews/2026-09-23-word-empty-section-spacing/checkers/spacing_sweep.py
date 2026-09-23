"""Private what-if only; final acceptance must re-render the source-built package."""
import concurrent.futures,json,os,subprocess,zipfile
from pathlib import Path
from lxml import etree
os.umask(0o077)
ROOT=Path(__file__).resolve().parent
PRIOR=Path('/home/trc/.local/share/dsw-word-empty-sections.lbeV2Q/candidate')
IMAGE='sha256:d71ab8c13b6bd47c7bc81195082005dfb17eaa75e8b1fadd347a64ee66ed98d5'
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main';NS={'w':W};A='{'+W+'}'
def task(case,before,after):
    source=PRIOR/'renders'/f'{case}-zh-Hant-submission/document.docx'
    target=ROOT/'sweep'/f'{before}-{after}'/case;target.mkdir(parents=True)
    with zipfile.ZipFile(source) as old,zipfile.ZipFile(target/'document.docx','w') as new:
        for item in old.infolist():
            value=old.read(item.filename)
            if item.filename=='word/document.xml':
                xml=etree.fromstring(value);count=0
                for props in xml.findall('.//w:pPr',NS):
                    style=props.find('w:pStyle',NS);spacing=props.find('w:spacing',NS)
                    if style is not None and style.get(A+'val')=='Heading2' and spacing is not None:
                        assert spacing.attrib=={A+'before':'120',A+'after':'60'}
                        spacing.set(A+'before',str(before));spacing.set(A+'after',str(after));count+=1
                assert count==5
                value=etree.tostring(xml,xml_declaration=True,encoding='UTF-8',standalone=True)
            new.writestr(item,value)
    command=['docker','run','--rm','--network','none','--log-driver','none','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--user','1000:1000','--entrypoint','/usr/bin/soffice',
        '-v',str(target)+':/data','-v',str(PRIOR/'packages/zh-Hant/src/fonts')+':/usr/local/share/fonts/private-audit:ro',
        IMAGE,'-env:UserInstallation=file:///tmp/private-office-profile','--headless','--nologo','--nodefault',
        '--nofirststartwizard','--convert-to','pdf','--outdir','/data','/data/document.docx']
    with (target/'conversion.log').open('x') as log:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    bbox=etree.fromstring(subprocess.check_output(['pdftotext','-bbox-layout',str(target/'document.pdf'),'-']))
    pages=bbox.findall('.//{*}page');words=pages[-1].findall('.//{*}word')
    text=''.join(''.join(w.itertext()) for w in words)
    if text.endswith(str(len(pages))+'/'+str(len(pages))):text=text[:-(len(str(len(pages)))*2+1)]
    title=''.join(t.text or '' for t in xml.findall('.//w:body/w:p',NS)[-1].findall('.//w:t',NS))
    compact=lambda t:''.join(t.split())
    row=dict(case=case,before_twips=before,after_twips=after,pages=len(pages),q15_alone=compact(text)==compact(title),
        diagnostic_only=True,source_built_acceptance=False)
    print(json.dumps(row),flush=True);return row
def main():
    tasks=[(case,before,40) for before in [80,60,40] for case in ['MISSING','NEGATIVE','POSITIVE','LONG']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(lambda t:task(*t),tasks))
    with (ROOT/'spacing-sweep.json').open('x') as f:json.dump(rows,f,indent=2)
if __name__=='__main__':main()
