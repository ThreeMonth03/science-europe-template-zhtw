from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from lxml import etree as ET
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from reduce_word_layout_case import LABEL, W, reduce_case, retained_nodes, text
from diagnose_word_import_layout import sha


class WordReductionTests(unittest.TestCase):
    def test_both_languages_keep_exact_q1_q5_xml_and_other_package_parts(self):
        for language in ('chinese', 'english'):
            source = ROOT / 'reviews/2026-09-17-storage-context-pagination/after/native' / ('metadata-partial-' + language + '.docx')
            digest = sha(source)
            with tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / 'reduced.docx'
                self.assertEqual(reduce_case(source, target), 53)
                with zipfile.ZipFile(source) as old, zipfile.ZipFile(target) as new:
                    self.assertEqual(old.namelist(), new.namelist())
                    for name in old.namelist():
                        if name != 'word/document.xml': self.assertEqual(old.read(name), new.read(name), name)
                    original = ET.fromstring(old.read('word/document.xml'))
                    expected, br, section = retained_nodes(original)
                    body = ET.fromstring(new.read('word/document.xml')).find(W + 'body')
                    xml = lambda n: ET.tostring(n, method='c14n', exclusive=True)
                    self.assertEqual([xml(n) for n in list(body)[2:-1]], [xml(n) for n in expected])
                    self.assertEqual(xml(body[-1]), xml(section))
                    self.assertEqual(text(body[0]), LABEL)
                    self.assertFalse(list(body.iter(W + 'bookmarkStart')))
                    self.assertFalse(any(text(n).startswith('6. ') for n in body))
                with self.assertRaises(FileExistsError): reduce_case(source, target)
            self.assertEqual(sha(source), digest)

    def test_missing_section_heading_is_rejected(self):
        source = ROOT / 'reviews/2026-09-17-storage-context-pagination/after/native/metadata-partial-chinese.docx'
        with zipfile.ZipFile(source) as z: original = ET.fromstring(z.read('word/document.xml'))
        body = original.find(W + 'body')
        first = next(n for n in body if text(n).startswith('第 1 節'))
        body.remove(first)
        with self.assertRaises(ValueError): retained_nodes(original)


if __name__ == '__main__': unittest.main()
