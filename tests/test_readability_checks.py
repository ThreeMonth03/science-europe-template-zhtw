import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_pilot import docx_has_table_headers


class ReadabilityChecks(unittest.TestCase):
    def test_budget_table_does_not_mask_broken_markdown_table(self):
        xml = ET.fromstring('''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:tbl><w:tr><w:tc><w:p><w:r><w:t>預算</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>''')
        self.assertFalse(docx_has_table_headers(xml, {"紀錄", "保存期間"}))
        self.assertTrue(docx_has_table_headers(xml, {"預算"}))

    def test_header_can_span_word_text_runs(self):
        xml = ET.fromstring('''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:tbl><w:tr><w:tc><w:p><w:r><w:t>紀錄</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>保存</w:t></w:r><w:r><w:t>期間</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>''')
        self.assertTrue(docx_has_table_headers(xml, {"紀錄", "保存期間"}))
