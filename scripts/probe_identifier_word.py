"""Run the actual worker Pandoc/Lua against bounded and rejected Q13 headings."""
import argparse
import json
from pathlib import Path
import subprocess
from artifact_utils import sha

RUNNER = '''import json,sys,tempfile,subprocess
from pathlib import Path
p=json.load(sys.stdin)
with tempfile.TemporaryDirectory(prefix="identifier-lua-") as tmp:
    f=Path(tmp)/"pilot.lua"
    f.write_text(p["lua"])
    ast=subprocess.check_output(["pandoc","--from=html","--to=json","--lua-filter="+str(f)],input=p["html"].encode())
    print(ast.decode())
'''


def paragraph_count(node):
    if isinstance(node,dict): return (node.get('t') in ['Para','Plain']) + sum(paragraph_count(v) for v in node.values())
    if isinstance(node,list): return sum(paragraph_count(v) for v in node)
    return 0


def words(node):
    if isinstance(node,dict):
        if node.get('t') == 'Str': return node['c']
        return ''.join(words(v) for k,v in node.items() if k=='c')
    if isinstance(node,list): return ''.join(words(v) for v in node)
    return ''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True); p.add_argument('--prior',type=Path,required=True)
    p.add_argument('--container',default='science-europe-pilot-docworker-1'); a=p.parse_args()
    assert a.container=='science-europe-pilot-docworker-1', 'Use the isolated pilot worker only'
    fixtures=[('english','<p><strong>Distribution 1</strong></p><p><strong>Institutional repository</strong></p>',True),
              ('chinese','<p><strong>資料提供管道 1</strong></p><p><strong>機構資料儲存庫</strong></p>',True),
              ('unicode-bound','<p><strong>'+('中'*80)+'</strong></p><p><strong>'+('文'*80)+'</strong></p>',True),
              ('single','<p><strong>Repository</strong></p>',True),
              ('empty-type','<p><strong>Distribution 1</strong></p><p></p>',True),
              ('too-long','<p><strong>'+('中'*241)+'</strong></p><p><strong>Type</strong></p>',False),
              ('three-labels','<p><strong>One</strong></p><p><strong>Two</strong></p><p><strong>Three</strong></p>',False),
              ('authored','<p><strong>Label</strong></p><p>Author prose.</p>',False),
              ('list','<p><strong>Label</strong></p><ul><li>Author item.</li></ul>',False),
              ('nested','<p><strong>Label</strong></p><div class="answer-detail"><p>First author paragraph.</p><p>Second author paragraph.</p></div>',False),
              ('mixed','<p><strong>Label</strong> <em>Additional prose.</em></p>',False)]
    html=''.join(f'<div id="{name}" class="identifier-heading">{body}</div>' for name,body,_ in fixtures)
    html+='<div id="outside"><p><strong>Unrelated label</strong></p><p>Unrelated answer.</p></div>'
    asts=[]
    for root in [a.prior,a.build]:
        lua=root/'en/src/word/pilot.lua'
        assert sha(lua)==sha(root/'translated/src/word/pilot.lua')
        ast=json.loads(subprocess.check_output(['docker','exec','-i',a.container,'python','-c',RUNNER],input=json.dumps({'lua':lua.read_text(),'html':html}).encode()))
        asts.append({b['c'][0][0]:b for b in ast['blocks']})
    checks=[]
    for name,_,merged in fixtures:
        before,after=[v[name] for v in asts]
        if merged:
            assert paragraph_count(after)==1
            assert ['custom-style','Pilot Label'] in after['c'][0][2]
            assert words(before)==words(after), (name,'Text changed')
        else: assert before==after, (name,'Unexpected flattening of rejected heading')
        checks.append({'case':name,'merged':merged,'passed':True})
    assert asts[0]['outside']==asts[1]['outside']
    report={'passed':True,'release_acceptance':False,'checks':checks,'outside_ast_unchanged':True,
            'checker_sha256':sha(Path(__file__)),
            'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
            'prior_package_sha256':{n:sha(a.prior/n) for n in ['english.zip','chinese.zip']},
            'lua_sha256':sha(a.build/'en/src/word/pilot.lua'),'prior_lua_sha256':sha(a.prior/'en/src/word/pilot.lua'),
            'pandoc_version':subprocess.check_output(['docker','exec',a.container,'pandoc','--version'],text=True).splitlines()[0],
            'worker_image_id':subprocess.check_output(['docker','inspect','--format','{{.Image}}',a.container],text=True).strip(),
            'limits':['Real worker Lua AST tests, not rendered full documents','No Microsoft Word pagination acceptance']}
    (a.build/'identifier-word-probe.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'cases':len(checks)}))


if __name__=='__main__': main()
