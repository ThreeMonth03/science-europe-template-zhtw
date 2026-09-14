"""Render and assert bilingual fixture behavior in HTML, PDF and DOCX."""

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ("q-how-data", "q-store-backup", "q-required-resources")
TABLE_CASES = {"populated", "partial", "stress", "representative", "retention-partial", "structured", "structured-partial", "storage-sharing", "storage-sharing-partial", "narrative-long", "quality-rich", "quality-partial", "reading-rich", "reading-partial", "table-long"}
TABLE_CASES.update({'format-rich', 'format-partial'})
TABLE_CASES.update({'sharing-custom', 'sharing-missing'})
TABLE_CASES.update({'preservation-complete', 'preservation-partial', 'preservation-custom', 'preservation-no-cold'})
TABLE_CASES.add('support-mixed')


def docx_has_table_headers(xml, headers):
    """Match header cells, not arbitrary tables or individual Word text runs."""
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    for table in xml.findall(".//w:tbl", ns):
        first = table.find("w:tr", ns)
        if first is None:
            continue
        cells = {
            "".join(text.text or "" for text in cell.findall(".//w:t", ns)).strip()
            for cell in first.findall("w:tc", ns)
        }
        if set(headers).issubset(cells):
            return True
    return False


def read_html(path):
    return BeautifulSoup(path.read_text(), "html.parser")


def facts(document):
    result = []
    for question in QUESTIONS:
        root = document.find(id=question)
        assert root is not None, question
        for element in root.select("[data-fact-id]"):
            item = element.find_parent(attrs={"data-item-id": True})
            result.append(
                (
                    question,
                    item.get("data-item-id") if item else None,
                    element["data-fact-id"],
                    element.get("data-status"),
                )
            )
    return sorted(result, key=str)


def validate_archive_only(document):
    q1 = document.find(id='q-how-data'); q5 = document.find(id='q-store-backup')
    q6 = document.find(id='q-access-security')
    assert q1.select_one('[data-fact-id="new-data"][data-status="missing"]')
    assert q5.select_one('[data-fact-id="during-project-archive"][data-status="complete"]')
    assert q5.select_one('[data-fact-id="archive-frequent-backup-need"][data-status="explicit-no"]')
    assert q6.select_one('[data-status="missing-output"]'), 'A cross-reference is not a security answer'
    assert q6.select_one('a[href="#q-store-backup"]')


def validate(build, cases):
    checks = []
    issues = []
    for case in cases:
        documents = {
            language: read_html(build / "renders" / f"{case}-{language}.html")
            for language in ("english", "chinese")
        }
        assert facts(documents["english"]) == facts(documents["chinese"]), (
            f"{case}: bilingual facts"
        )
        for language, document in documents.items():
            assert len(document.select(".question > h3")) == 15, f"{case}: missing question"
            for question in QUESTIONS:
                root = document.find(id=question)
                assert not root.select("p p, p ul, p div, p table"), (
                    f"{case}/{question}: nested block in paragraph"
                )
                assert "Information not provided:" not in root.get_text() or language == "english"
            q1, q5, q15 = (document.find(id=q) for q in QUESTIONS)
            if case == "empty":
                assert q1.select_one('[data-fact-id="new-data"][data-status="missing"]')
                assert not q1.select('[data-status="explicit-no"]')
                assert q5.select_one('[data-fact-id="backup-arrangement"][data-status="missing"]')
            elif case == "negative":
                assert q1.select_one('[data-fact-id="new-data"][data-status="explicit-no"]')
                assert q5.select_one(
                    '[data-fact-id="backup-reliability"][data-status="explicit-no"]'
                )
            elif case == "partial":
                assert q1.select_one('[data-fact-id="reuse-purpose"][data-status="missing"]')
                assert q1.select_one('[data-fact-id="reuse-purpose"][data-status="complete"]')
                assert "5000" in q15.get_text(), "Missing currency suppressed the supplied amount"
                assert q15.select_one('[data-fact-id="resource-amount"][data-status="missing"]')
            elif case == 'archive-only':
                validate_archive_only(document)
            else:
                assert len(q1.select('[data-fact-id="reuse-purpose"][data-status="complete"]')) == 2
                assert "5000 TWD" in q15.get_text(" ", strip=True)
                assert "0 TWD" in q15.get_text(" ", strip=True), "Zero cost must not become missing"
            if case in TABLE_CASES:
                if not q1.select_one(".answer-detail table"):
                    issues.append(
                        {
                            "case": case,
                            "language": language,
                            "code": "markdown-table-unsupported",
                            "message": "DSW 4.30 prints the pipe table as text; table acceptance is blocked",
                        }
                    )
                assert q15.select_one(".answer-detail ul"), "Markdown list lost"
            pdf = build / "renders" / f"{case}-{language}.pdf"
            assert pdf.read_bytes().startswith(b"%PDF"), str(pdf)
            docx = build / "renders" / f"{case}-{language}.docx"
            with zipfile.ZipFile(docx) as archive:
                assert archive.testzip() is None
                xml = ET.fromstring(archive.read("word/document.xml"))
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                content = " ".join(n.text or "" for n in xml.findall(".//w:t", ns))
                if case in TABLE_CASES:
                    assert "5000" in content, "Word lost the budget amount"
                    table_headers = {"Record", "Retention"} if language == "english" else {"紀錄", "保存期間"}
                    has_provenance_table = docx_has_table_headers(xml, table_headers)
                    if not has_provenance_table:
                        issues.append(
                            {
                                "case": case,
                                "language": language,
                                "code": "docx-table-missing",
                                "message": "Word contains no editable provenance table; template-owned budget tables do not satisfy this check",
                            }
                        )
                assert "Noto Sans CJK TC" in archive.read("word/styles.xml").decode()
            checks.append(
                {"case": case, "language": language, "facts": len(facts(document)), "passed": True}
            )
    return checks, issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--english", type=Path, required=True)
    parser.add_argument("--tooling", type=Path, required=True)
    parser.add_argument(
        "--cases", nargs="+", default=["empty", "negative", "partial", "populated", "stress"]
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    build = args.build.resolve()

    def render(job):
        case, language, output_format = job
        locale = "en" if language == "english" else "zh-Hant"
        command = [
            sys.executable,
            str(ROOT / "scripts/render.py"),
            "--build",
            str(build),
            "--project",
            str(args.english.resolve() / f"fixtures/pilot/{locale}/{case}.json"),
            "--language",
            language,
            "--format",
            output_format,
            "--name",
            case,
            "--tooling",
            str(args.tooling.resolve()),
        ]
        result = subprocess.run(command, text=True, capture_output=True)
        (build / f"render-{case}-{language}-{output_format}.log").write_text(
            result.stdout + result.stderr
        )
        print(
            f"{case}/{language}/{output_format}: {'OK' if result.returncode == 0 else 'FAILED'}",
            flush=True,
        )
        return {
            "case": case,
            "language": language,
            "format": output_format,
            "passed": result.returncode == 0,
        }

    if not args.validate_only:
        jobs = [
            (case, language, fmt)
            for case in args.cases
            for language in ("english", "chinese")
            for fmt in ("html", "pdf", "docx")
        ]
        # Package installation is not atomic across concurrent DSW imports.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            results = list(executor.map(render, jobs))
        (build / "render-results.json").write_text(json.dumps(results, indent=2) + "\n")
        if not all(r["passed"] for r in results):
            raise SystemExit("Rendering failed; see build-local logs")
    checks, issues = validate(build, args.cases)
    report = {
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "passed": not issues,
        "semantic_checks_passed": True,
        "checks": checks,
        "blocking_issues": issues,
        "package_sha256": {
            name: hashlib.sha256((build / name).read_bytes()).hexdigest()
            for name in ("english.zip", "chinese.zip")
        },
        "sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((build / "renders").iterdir())
            if p.is_file()
        },
        "limits": [
            "Q1/Q5/Q15 only",
            "Human visual review is separate",
            "Microsoft Word opening is not tested",
        ],
    }
    (build / "pilot-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "Pilot semantic checks passed; "
        + ("acceptance BLOCKED (see report)" if issues else "file checks passed")
    )
    if issues:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
