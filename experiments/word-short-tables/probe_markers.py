"""Read-only-format experiment: test which raw markers Pandoc retains."""
import json
from pathlib import Path
import subprocess

IMAGE = 'sha256:6d3cbcab3294e760a4d92e27bec72d4fb23a0adb2cc1734d981478688741ab11'
RUNNER = r'''import json,subprocess,tempfile,zipfile
from pathlib import Path
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)
    rows={}
    for name,markers in {
        'comment': ['<!--DSW-SHORT-START-->', '<!--DSW-SHORT-END-->'],
        'bookmark': ['<w:bookmarkStart w:id="2147483000" w:name="DswShortStart"/>', '<w:bookmarkEnd w:id="2147483000"/>'],
    }.items():
        lua='function Table(t) return {pandoc.RawBlock("openxml", '+json.dumps(markers[0])+'),t,pandoc.RawBlock("openxml", '+json.dumps(markers[1])+')} end'
        (p/'f.lua').write_text(lua)
        subprocess.run(['pandoc','-f','html','-t','docx','--lua-filter='+str(p/'f.lua'),'-o',str(p/'o.docx')],
                       input=b'<p>Before.</p><table><tr><th>Item</th><th>Value</th></tr><tr><td>N/A</td><td>0</td></tr></table><p>After.</p>',check=True)
        with zipfile.ZipFile(p/'o.docx') as z: rows[name]=z.read('word/document.xml').decode()
    print(json.dumps({'pandoc':subprocess.check_output(['pandoc','--version'],text=True).splitlines()[0],'rows':rows}))
'''

if __name__ == '__main__':
    result = json.loads(subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '--read-only',
        '--tmpfs', '/tmp:rw,size=128m', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
        '--entrypoint', 'python', IMAGE, '-c', RUNNER]))
    print(json.dumps(result, indent=2))
