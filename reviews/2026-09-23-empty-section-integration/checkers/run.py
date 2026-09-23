import concurrent.futures,importlib.util,itertools,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def load(name):
    spec=importlib.util.spec_from_file_location('sections_'+name,ROOT/'candidate'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def main():
    assert subprocess.check_output(['docker','image','inspect','gotenberg/gotenberg:8','--format','{{.Id}}'],text=True).strip()=='sha256:d71ab8c13b6bd47c7bc81195082005dfb17eaa75e8b1fadd347a64ee66ed98d5'
    module=load('run_matrix');contexts=json.loads((ROOT/'manifest.json').read_text())['contexts']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows=[]
        for row in pool.map(lambda task:module.run(*task),itertools.product(sorted(contexts),['en','zh-Hant'],['review','submission'])):
            rows.append(row);print(json.dumps(row),flush=True)
    (ROOT/'renders.json').write_text(json.dumps(rows,indent=2)+'\n')
    assert len(rows)==28 and all(r['passed'] for r in rows)
    module=load('render_word_previews');rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for row in pool.map(module.run,[p.parent for p in sorted((ROOT/'candidate/renders').glob('*/document.docx'))]):
            rows.append(row);print(json.dumps(row),flush=True)
    (ROOT/'previews.json').write_text(json.dumps(rows,indent=2)+'\n')
    assert len(rows)==28 and all(r['passed'] for r in rows)
if __name__=='__main__':main()
