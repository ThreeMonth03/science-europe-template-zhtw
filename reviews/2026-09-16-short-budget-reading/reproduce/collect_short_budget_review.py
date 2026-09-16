"""Archive verified native bilingual short-budget comparisons and rejected trials."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_short_budget_outputs import CASES, NEW_BASELINES

ROOT = Path(__file__).resolve().parents[1]


def read(root, name): return json.loads((root/name).read_text())


def verify(root, hashes):
    for name, digest in hashes.items(): assert sha(root/name) == digest, (root, name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['build', 'candidate', 'rebuild', 'prior', 'extra-prior', 'rejected', 'preflight', 'compact-preflight', 'english', 'destination']:
        p.add_argument('--'+key, type=Path, required=True)
    a = p.parse_args(); assert not a.destination.exists()
    report = read(a.build, 'short-budget-report.json'); assert report['selected_checks_passed']
    expected = {(c, l) for c in CASES for l in ['english', 'chinese']}
    assert len(report['rows']) == 14 and {(r['case'], r['language']) for r in report['rows']} == expected
    assert all(not r['errors'] and not r['reading_issues'] for r in report['rows'])
    for root in [a.build, a.candidate, a.rebuild]: verify(root, report['package_sha256'])
    for root, count in [(a.build, 42), (a.extra_prior, 12), (a.rejected, 42)]:
        render = read(root, 'missing-info-render-report.json')
        assert render['all_renders_succeeded'] and len(render['renders']) == count and all(r['rendered'] for r in render['renders'])
        cleanup = read(root, 'owned-test-template-cleanup.json')
        assert len(cleanup['deleted']) == 2 and cleanup['project_references'] == cleanup['document_references'] == 0
    before_hashes = read(a.prior, 'missing-info-render-report.json')['package_sha256']
    assert before_hashes == read(a.extra_prior, 'missing-info-render-report.json')['package_sha256']
    for root in [a.prior, a.extra_prior]: verify(root, before_hashes)
    state = read(a.build, 'runtime-restoration.json')
    assert state['stock_worker_restored'] and len(state['services']) == 4 and all(not s['running'] for s in state['services'])
    recovery = read(a.build, 'worker-recovery.json')
    assert recovery['same_image_verified'] and recovery['all_42_original_requests_completed']
    assert recovery['render_report_sha256'] == sha(a.build/'missing-info-render-report.json')
    copies = []; excerpts = {}
    def keep(source, target): copies.append((source, Path(target)))
    rejected = read(a.rejected, 'rejection.json'); assert rejected['accepted'] is False
    verify(a.rejected, rejected['package_sha256']); verify(a.rejected, rejected['artifact_sha256'])
    for name in ['rejection.json', 'ci-status.json', 'manifest.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json']:
        keep(a.rejected/name, 'diagnostics/rejected-native/'+name)
    for name in rejected['artifact_sha256']: keep(a.rejected/name, 'diagnostics/rejected-native/'+name)
    for row in report['rows']:
        verify(a.build, row['artifact_sha256'])
        for name, digest in row['prior_artifact_sha256'].items(): assert sha(Path(name)) == digest
        stem = row['case']+'-'+row['language']; prior = a.extra_prior if row['case'] in NEW_BASELINES else a.prior
        for side, root in [('before', prior), ('after', a.build)]:
            for fmt in ['pdf', 'docx']:
                for extra in ['', '.fixture.json']:
                    name = stem+'.'+fmt+extra; keep(root/'renders'/name, side+'/native/'+name)
            keep(root/'renders'/(stem+'.html.fixture.json'), side+'/native/'+stem+'.html.fixture.json')
            keep(root/'word-preview'/(stem+'.pdf'), side+'/word-preview/'+stem+'.pdf')
        source = a.build/'renders'/(stem+'.html'); soup = BeautifulSoup(source.read_text(), 'html.parser')
        excerpts['question-content/'+stem+'.html'] = '<!-- Exact native question excerpt; full HTML SHA256: '+sha(source)+' -->\n'+str(soup.select_one('#dmp-content'))+'\n'
        locale = 'en' if row['language'] == 'english' else 'zh-Hant'
        for suffix in ['.json', '.events.json']: keep(a.english/'fixtures/pilot'/locale/(row['case']+suffix), 'fixtures/'+locale+'/'+row['case']+suffix)
    for name in ['short-budget-report.json', 'manifest.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json', 'runtime-restoration.json', 'worker-exit-139.json', 'worker-recovery.json']:
        keep(a.build/name, 'after/'+name)
    for label, root in [('candidate', a.candidate), ('rebuild', a.rebuild)]:
        m = read(root, 'manifest.json'); assert m['status'] == 'candidate' and all(not c['dirty'] for c in m['checkouts'].values())
        keep(root/'manifest.json', label+'-manifest.json')
    for name in ['short-budget-scope.json', 'short-budget-english.json', 'short-budget-chinese.json', 'empty-pdf-probe-english.json', 'empty-pdf-probe-chinese.json', 'long-budget-english.json', 'long-budget-chinese.json']:
        assert read(a.candidate, name)['passed']; keep(a.candidate/name, 'probes/'+name)
    for name in ['manifest.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json']:
        keep(a.extra_prior/name, 'before/extra-cases-'+name)
    for root, label in [(a.preflight, 'width-trials'), (a.compact_preflight, 'compact-trial')]:
        trial = read(root, 'report.json'); assert trial['release_acceptance'] is False
        source = (ROOT/'scripts/rehearse_short_budget.py').read_text()
        if label == 'width-trials':
            source = ''.join(line for line in source.splitlines(keepends=True) if not line.startswith("VARIANTS['width-49-compact']="))
        assert hashlib.sha256(source.encode()).hexdigest() == trial['checker_sha256']
        excerpts['diagnostics/'+label+'/rehearse_short_budget.py'] = source
        for f in sorted(root.glob('*')):
            if f.suffix in ['.json', '.pdf']: keep(f, 'diagnostics/'+label+'/'+f.name)
    for f in sorted(a.build.glob('*.png')): keep(f, 'page-samples/'+f.name)
    for name in ['collect_short_budget_review.py', 'check_short_budget_outputs.py', 'probe_short_budget_scope.py', 'rehearse_short_budget.py', 'cleanup_owned_runtime_templates.py']:
        keep(ROOT/'scripts'/name, 'reproduce/'+name)
    keep(a.english/'scripts/probe_short_budget.py', 'reproduce/probe_short_budget.py')
    keep(a.english/'scripts/probe_pdf_budget_reading.py', 'reproduce/probe_pdf_budget_reading.py')
    keep(ROOT/'pipeline.yml', 'reproduce/pipeline.yml')
    for source, _ in copies: assert source.is_file(), source
    a.destination.mkdir(parents=True)
    for source, name in copies:
        target = a.destination/name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
    for name, content in excerpts.items():
        target = a.destination/name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(content)
    rows = {(r['case'], r['language']): r for r in report['rows']}
    table = ['| 案例 | EN PDF 前 → 後 | ZH PDF 前 → 後 | EN / ZH Word 頁數（不變） |', '|---|---:|---:|---:|']
    for case in CASES:
        en, zh = [rows[case, l] for l in ['english', 'chinese']]
        table.append(f"| {case} | {en['prior_pages']} → {en['pages']} | {zh['prior_pages']} → {zh['pages']} | {en['word_pages']} / {zh['word_pages']} |")
    doc = '''# 0.3.25：部分漏填的短預算表與整份 PDF

中文 partial 原生 PDF 從 5 頁減為 4 頁，短預算表不再單獨留在稀疏尾頁。
缺幣別提示中文 2 → 1 行、英文 4 → 2 行；英文整份仍是 5 頁，未宣稱
其尾頁留白已解決。這次不改中文措辭，不改原始回答或隱藏缺答。

先看 [中文前版](before/native/partial-chinese.pdf) →
[中文新版](after/native/partial-chinese.pdf)，以及
[英文前版](before/native/partial-english.pdf) →
[英文新版](after/native/partial-english.pdf)。
混合漏填：[中文 PDF](after/native/budget-mixed-gaps-chinese.pdf)、
[英文 PDF](after/native/budget-mixed-gaps-english.pdf)。
Word 控制：[中文](after/native/partial-chinese.docx)、
[英文](after/native/partial-english.docx)。

## 原生比較

七組中英共 42 個原生輸出（14 HTML、14 PDF、14 DOCX），另有 14 份
LibreOffice 預覽。混合漏填／八筆預算先以真正 0.3.24 補產 12 個基準
輸出；其他基準取自前輪保留的 0.3.24。輸入配方、事件與 KM hash 相同。

所有十五題 HTML 完全相同；PDF 題目正文、缺答與自填段落保留，沒有新增
頁數，非目標控制組的正文分頁完全相同。所有 Word 本文 XML、樣式、外部
連結與預覽頁數不變。漏幣別的長回答仍保留 60 段、5000、第二筆 0 TWD
及續頁資源資訊。詳見 `after/short-budget-report.json`。
partial 的兩個培訓清單圓點由引擎在每頁最後繪製，raw 抽取順序會隨表格
移頁改變；比對先核對兩個圓點與清單行的座標、數量及內容，再恢復其視覺
順序。沒有刪掉所有圓點或放寬作者原文、標點的相同比對。

'''+ '\n'.join(table)+'''

## 變更範圍與版本

英文 `src/budget-reading.html.j2` 增加保守判斷：1–3 列、原有預算缺答、
短文字、有限段落與已知 HTML 才加 PDF 專用 class。未知／長／複雜內容
回到原版型；已有長預算排版的表格不改。CSS 只調欄寬與內距，字級、行距
不變。這些條件不是通用 HTML 驗證器，也不能保證所有任意輸入的頁高。

中英各 42 組短表格原樣保留／邊界測試、32 組既有長表格測試、13 組空白
Q15 引擎測試通過。731 個翻譯檔與其餘 prepared src 不變；去掉新增 helper
與 CSS 後，與 0.3.24 逐位元一致。Q15 的問題與回覆邏輯沒有再改。

兩個 repo 同用 `fix/short-budget-reading`；中文仍由既有翻譯樹建置，
`pipeline.yml` 鎖英文 commit 與工具 commit，不另養一套中文 Jinja。
未升級官方 upstream、合併 main、建立 tag 或發布。未來 upstream 若改
Q15 的捕捉結構，需要重跑兩語言與各格式測試，不能只靠 Git 無衝突。

## 保留的未採用方案與限制

第一版原生 partial PDF 印出 `<table ...>` 文字而失去表格，已拒收並保存於
`diagnostics/rejected-native`。原因是 Jinja autoescape 把新增的固定開頭
標籤跳脫；修正版只對該固定字串使用 safe，不將使用者輸入改為安全 HTML。
42 組測試現在同時跑自動跳脫開／關，另測作者標題仍被跳脫。第一版 CI
通過不足以證明成品可用，修正版另以完整七組原生輸出重測。

`diagnostics/width-trials` 保留 40/29/31 欄寬：提示雖變短，英文用途被擠窄，
表格反而更高。49/25/26 加小幅內距調整才進原生驗證。這些試算用凍結
HTML 和固定引擎，不冒充 DSW 原生輸出；原生結果在 `before/after`。

仍是局部實驗，不是所有問卷分支、Science Europe 實質內容、整份中英語氣
或 Microsoft Word 實機驗收。英文稀疏尾頁與 stock worker 的 Markdown
表格問題仍是後續工作／發布門檻。字型替代也可能改變 Word 分頁。
Word 的短預算缺幣別提示仍有窄欄折行（這批預覽中文兩行、英文三行）；
本輪只證明 Word 沒退步，不代表這個閱讀問題已修好，列為下一步。
修正版完成第 41 份輸出後，本機 patched worker 發生一次非 OOM 的 exit 139。
保留狀態後重啟相同映像，原等待中的最後一份 Word 正常完成，未改套件或
略過案例。這是故障復原，不是根因修復；`after/worker-exit-139.json` 與
`after/worker-recovery.json` 保留紀錄，runtime 穩定性仍是發布前待查問題。

僅操作本機合成資料；沒有讀取 keyring 或修改線上 DSW。前版／新版各兩個
暫存模板，以及拒收版的兩個暫存模板，核對無引用後清理，ZIP 備份可重建；原版 worker 已恢復，四個
pilot 服務停止，沒有刪除 volumes。完整 HTML 留在本機並記 hash，repo
保存題目摘錄、原生 PDF/DOCX、預覽、檢查與來源紀錄。
'''
    (a.destination/'README.md').write_text(doc)
    hashes = {str(f.relative_to(a.destination)): sha(f) for f in sorted(a.destination.rglob('*')) if f.is_file()}
    (a.destination/'checksums.json').write_text(json.dumps(hashes, indent=2)+'\n')
    print(json.dumps({'archive': str(a.destination), 'verified_files': len(hashes)}))


if __name__ == '__main__': main()
