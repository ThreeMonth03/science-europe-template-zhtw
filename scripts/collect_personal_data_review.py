"""Archive one exact 0.3.21 native matrix; never overwrite historical evidence."""
import argparse
import json
from pathlib import Path
import shutil
from bs4 import BeautifulSoup
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]
CASES = ['personal-followups-empty', 'personal-transfer-missing', 'personal-transfer-complete',
         'personal-transfer-no', 'personal-data-partial', 'empty', 'negative', 'preservation-complete']


def read(root, name): return json.loads((root/name).read_text())


def verify(root, hashes):
    for name, expected in hashes.items(): assert sha(root/name) == expected, ('Evidence drift', root, name)


def source_scope(before, after):
    rows = []
    for part in ['en', 'translated']:
        left = {str(p.relative_to(before/part)): sha(p) for p in (before/part/'src').rglob('*') if p.is_file()}
        right = {str(p.relative_to(after/part)): sha(p) for p in (after/part/'src').rglob('*') if p.is_file()}
        assert left.keys() == right.keys()
        changed = sorted(k for k in left if left[k] != right[k])
        assert changed == ['src/questions/07-personal-data.html.j2', 'src/questions/09-ethical-issues.html.j2']
        rows.append({'language': part, 'files': len(left), 'changed': changed, 'before': left, 'after': right})
    return {'passed': True, 'scope': 'Prepared src files including PDF/Word styles and fonts; package version metadata intentionally changes',
            'before_package_sha256': {n: sha(before/n) for n in ['english.zip', 'chinese.zip']},
            'after_package_sha256': {n: sha(after/n) for n in ['english.zip', 'chinese.zip']}, 'rows': rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['build', 'candidate', 'rebuild', 'prior-candidate', 'english', 'destination']:
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); assert not a.destination.exists()
    report = read(a.build, 'personal-data-report.json')
    assert report['selected_checks_passed'] and len(report['rows']) == 16
    expected = {(c, l) for c in CASES for l in ['english', 'chinese']}
    assert {(r['case'], r['language']) for r in report['rows']} == expected
    assert all(not r['errors'] and not r['reading_issues'] for r in report['rows'])
    verify(a.build, report['package_sha256']); verify(a.candidate, report['package_sha256']); verify(a.rebuild, report['package_sha256'])
    renders = read(a.build, 'missing-info-render-report.json')
    assert renders['all_renders_succeeded'] and len(renders['renders']) == 48
    assert {(r['case'], r['language'], r['format']) for r in renders['renders']} == {(c, l, f) for c, l in expected for f in ['html', 'pdf', 'docx']}
    assert all(r['rendered'] for r in renders['renders']) and len(renders['validation']) == 16
    assert all(not r['errors'] for r in renders['validation'])
    scope = source_scope(a.prior_candidate, a.candidate)
    continuity = read(a.build, 'q8-list-continuity.json')
    assert not continuity['passed'] and continuity['failures'], 'Preserve the observed whole-document counterexample'
    assert continuity['package_sha256'] == report['package_sha256']
    copies = []; excerpts = {}
    def keep(source, target): copies.append((source, Path(target)))
    for row in report['rows']:
        verify(a.build, row['artifact_sha256'])
        stem = row['case']+'-'+row['language']
        for fmt in ['pdf', 'docx']:
            for suffix in ['', '.fixture.json']:
                name = stem+'.'+fmt+suffix; keep(a.build/'renders'/name, 'native/'+name)
        keep(a.build/'renders'/(stem+'.html.fixture.json'), 'native/'+stem+'.html.fixture.json')
        keep(a.build/'word-preview'/(stem+'.pdf'), 'word-preview/'+stem+'.pdf')
        html = a.build/'renders'/(stem+'.html'); soup = BeautifulSoup(html.read_text(), 'html.parser')
        excerpts['question-content/'+stem+'.html'] = '<!-- Extracted from native HTML; full HTML SHA256: '+sha(html)+' -->\n'+str(soup.select_one('#dmp-content'))+'\n'
        locale = 'en' if row['language'] == 'english' else 'zh-Hant'
        for suffix in ['.json', '.events.json']:
            name = row['case']+suffix; keep(a.english/'fixtures/pilot'/locale/name, 'fixtures/'+locale+'/'+name)
    for name in ['manifest.json', 'missing-info-render-report.json', 'personal-data-report.json', 'owned-test-template-cleanup.json']:
        keep(a.build/name, name)
    keep(a.build/'q8-list-continuity.json', 'known-failures/q8-list-continuity.json')
    for path in sorted(a.build.glob('*.png')): keep(path, 'page-samples/'+path.name)
    for name in ['personal-data-translation-proof.json', 'missing-info-translation-proof.json', 'missing-info-group-probe.json']:
        assert read(a.candidate, name)['passed']; keep(a.candidate/name, 'probes/'+name)
    for label, root in [('candidate', a.candidate), ('rebuild', a.rebuild), ('prior-candidate', a.prior_candidate)]:
        m = read(root, 'manifest.json'); assert m['status'] == 'candidate' and all(not s['dirty'] for s in m['checkouts'].values())
        keep(root/'manifest.json', label+'-manifest.json')
    for name in ['check_personal_data_outputs.py', 'probe_personal_data_translation.py', 'collect_personal_data_review.py', 'run_missing_info.py', 'probe_q8_list_continuity.py']:
        keep(ROOT/'scripts'/name, 'reproduce/'+name)
    keep(a.english/'scripts/generate_personal_data_fixtures.py', 'reproduce/generate_personal_data_fixtures.py')
    keep(ROOT/'docs/personal-data-translation-delta.json', 'reproduce/personal-data-translation-delta.json')
    keep(ROOT/'pipeline.yml', 'reproduce/pipeline.yml')
    for source, _ in copies: assert source.is_file(), source
    a.destination.mkdir(parents=True)
    for source, target in copies:
        path = a.destination/target; path.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, path)
    for name, content in excerpts.items():
        path = a.destination/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)
    (a.destination/'probes/source-scope.json').write_text(json.dumps(scope, indent=2)+'\n')
    table = ['| 案例 | EN PDF / Word 預覽 | ZH PDF / Word 預覽 |', '|---|---:|---:|']
    rows = {(r['case'], r['language']): r for r in report['rows']}
    for case in CASES:
        en, zh = [rows[case, l] for l in ['english', 'chinese']]
        table.append(f"| {case} | {en['pages']} / {en['word_pages']} | {zh['pages']} / {zh['word_pages']} |")
    document = '''# 0.3.21：中英文個資追問、缺答與原段落

這是同一組已鎖定候選套件的 8 案例 × 2 語言驗證，共 16 份原生 PDF、16 份
DOCX、16 份 HTML；另產生 16 份 LibreOffice Word 預覽。不是 Microsoft Word
或整份 DMP 的正式驗收，也不是法律合規認證。

先看 [中文追問漏填 PDF](native/personal-followups-empty-chinese.pdf)、
[英文追問漏填 PDF](native/personal-followups-empty-english.pdf)、
[中文傳輸措施漏填 PDF](native/personal-transfer-missing-chinese.pdf)、
[英文傳輸措施漏填 PDF](native/personal-transfer-missing-english.pdf)。
有段落和清單的 [中文完整 PDF](native/personal-transfer-complete-chinese.pdf)、
[英文完整 PDF](native/personal-transfer-complete-english.pdf)，及對應
[中文 Word](native/personal-transfer-complete-chinese.docx)／
[英文 Word](native/personal-transfer-complete-english.docx) 可一起比較。

## 本輪修正

- Q7 追問漏填仍保留明確提示；選「其他法律依據」但沒填細項不再產生半句。
- 跨境傳輸「是但措施缺答」保留傳輸意向；明確「否」如實呈現，與漏填分開。
- 自由回答保留原段落、清單、強調與連結；Markdown 區塊不再巢狀放進段落。
- Q9 不把 Explore 當成完成評估，不自行宣稱公共利益高於隱私；其他依據缺答
  使用完整句指向 Q7。這些是忠實呈現填答，不是代替使用者判斷法規適用性。

## 驗證範圍

原有 718 組英中句對完整沿用；5 組移除／替換與 13 組新增均列入精確差異
檢查，共 731 單位。prepared source 的變動僅 Q7、Q9；CSS、Word Lua、reference
字型、其他問題與長／短預算程式未改。英文來源 commit 與候選／重建 ZIP hashes
見 manifest。所有本輪樣張來自同一組 ZIP，沒有跨候選拼接證據。

人工抽看中英文 Q7 缺答、完整 PDF 與 Word 後，額外發現中文完整 Word 的 Q8
第一個資料集名稱在第 4 頁尾端，授權說明在第 5 頁。這個跨頁反例尚未修正，
已有 [失敗報告](known-failures/q8-list-continuity.json) 與頁面樣張；Q7 自動檢查
通過不能覆蓋這項整份文件的閱讀缺陷。不能把這批成品稱為全部驗收通過。

原生檢查涵蓋 6 節／15 題存在、題答銜接、缺答提示、頁面邊界、Q7 原文順序、
中英 fact/status/ownership 對齊，以及 Word 文字與連結保留。empty、negative、
preservation-complete 六份控制組另核對 0.3.20 題目 HTML、Word 正文／樣式／
連結及 PDF 題目頁碼不變；完整閱讀品質不能只以頁數判斷。

'''+ '\n'.join(table)+'''

## 邊界與後續

短預算窄欄仍會將「幣別尚未提供」折行，整體留白未改。其他同意程序、DPIA
與 Q8 清單名稱／授權說明的 Word 連頁規則仍需修正或檢查。
與剩餘追問尚未全部稽核。原生輸出使用隔離本機的 Markdown-tables worker，
stock worker 表格仍是正式發布門檻；沒有讀取線上帳密或修改線上 project。
沒有合併 main、建立 tag／release 或部署。測試用暫存模板在確認無引用並保留
原 ZIP 後清理；回復 stock worker 並停止本輪四個本機 pilot 服務。

`native/` 是原生 PDF／DOCX，`word-preview/` 是 LibreOffice 預覽；
`question-content/` 是從原生 HTML 擷取的題目內容，非另一次渲染、非完整 HTML。
全文 HTML 保留在本機 runtime 目錄，其 hash 記在報告和擷取檔頭；不將嵌入字型
造成的大型 HTML 重複提交。`checksums.json` 覆蓋本審閱目錄的證據與說明。
'''
    (a.destination/'README.md').write_text(document)
    hashes = {str(f.relative_to(a.destination)): sha(f) for f in sorted(a.destination.rglob('*')) if f.is_file()}
    (a.destination/'checksums.json').write_text(json.dumps(hashes, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'archive': str(a.destination), 'verified_files': len(hashes)}))


if __name__ == '__main__': main()
