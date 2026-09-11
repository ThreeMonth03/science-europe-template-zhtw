"""Check specific readability regressions, not overall writing quality."""
import argparse
import json
import re
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup
from artifact_utils import sha
from run_pilot import docx_has_table_headers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    args = parser.parse_args()
    checks = []
    for case in ("empty", "negative", "partial", "populated", "stress"):
        for language in ("english", "chinese"):
            html = BeautifulSoup((args.build / "renders" / f"{case}-{language}.html").read_text(), "html.parser")
            questions = html.select(".question")
            assert len(questions) == len({q["id"] for q in questions}) == 15
            assert len(html.select(".dmp-section")) == 6
            assert len(html.select('[data-status="unmapped"]')) == 2
            assert "Did not apply for any funding yet" not in html.get_text()
            assert "尚未申請任何經費" not in html.get_text()
            if case in ("populated", "partial", "stress"):
                assert len(html.select('a[href="mailto:research@example.org"]')) == 1
                assert len(html.select(".shared-reference-policy")) == 1
                assert len(html.select('[data-fact-id="dataset-version"]')) == 2
                rows = html.select(".resource-table > tbody > tr")
                assert len(rows) == 2
                assert all(len(row.find_all("td", recursive=False)) == 3 for row in rows)
                assert rows[1].find_all("td", recursive=False)[1].get_text(strip=True) == "0 TWD"
                first_budget = rows[0].find_all("td", recursive=False)[1].get_text(" ", strip=True)
                assert "5000" in first_budget
                if case == "partial":
                    assert "TWD" not in first_budget
                    assert rows[0].select_one('[data-fact-id="resource-amount"][data-status="missing"]')
                with zipfile.ZipFile(args.build / "renders" / f"{case}-{language}.docx") as archive:
                    xml = ET.fromstring(archive.read("word/document.xml"))
                    headers = {"Resource and purpose", "Budget", "Funding source"} if language == "english" else {"資源項目與用途", "預算", "經費來源"}
                    assert docx_has_table_headers(xml, headers), "Native budget table missing"
                    if case == "stress":
                        sentence = "Long descriptive text to exercise pagination." if language == "english" else "此段較長的研究說明用於檢查跨頁排版、標點與中文字型。"
                        expected = "".join(sentence.split())
                        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                        word_text = "".join(node.text or "" for node in xml.findall(".//w:t", ns))
                        pdf_text = subprocess.check_output(["pdftotext", str(args.build / "renders" / f"{case}-{language}.pdf"), "-"], text=True)
                        # A generated footer can interrupt a sentence across pages.
                        # Remove only standalone page-counter lines, not body words.
                        pdf_text = re.sub(r"(?m)^\s*\d+\s*/\s*\d+\s*$", "", pdf_text)
                        assert "".join(word_text.split()).count(expected) == 80, "Word lost long-answer text"
                        assert "".join(pdf_text.split()).count(expected) == 80, "PDF lost long-answer text"
            checks.append({"case": case, "language": language, "passed": True})
    report = {
        "passed": True,
        "checks": checks,
        "checker_sha256": sha(Path(__file__)),
        "package_sha256": {name: sha(args.build / name) for name in ("english.zip", "chinese.zip")},
        "limits": ["Structural regressions only, not a prose-quality score", "Human page review and Microsoft Word acceptance remain separate"],
    }
    (args.build / "readability-checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Specific readability regressions passed (10 language/case pairs)")


if __name__ == "__main__":
    main()
