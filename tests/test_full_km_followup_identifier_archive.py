import hashlib
import json
from pathlib import Path
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-22-full-km-followups'
SEAL = '94f866ebbea8e4172dda380b30e50c24076280612b74930faf3aec14ba6acd69'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def locations(path):
    xml = ET.fromstring(subprocess.check_output(['pdftotext', '-bbox-layout', str(path), '-']))
    result = {}
    for page_index, page in enumerate(xml.findall('.//{*}page'), 1):
        for line_index, line in enumerate(page.findall('.//{*}line')):
            for word in line.findall('.//{*}word'):
                if word.text in ['ARK:', 'ark:/12345/public-synthetic-control']:
                    result[word.text] = (page_index, line_index, word.get('xMin'), word.get('yMin'))
    assert len(result) == 2
    return result


class FullKmIdentifierArchiveTests(unittest.TestCase):
    def test_all_frozen_bytes_and_prototype_package_binding(self):
        self.assertEqual(sha(ARCHIVE / 'checksums.json'), SEAL)
        for name, expected in json.loads((ARCHIVE / 'checksums.json').read_text()).items():
            self.assertEqual(sha(ARCHIVE / name), expected, name)
        report = json.loads((ARCHIVE / 'native/report.json').read_text())
        build = json.loads((ARCHIVE / 'build/manifest.json').read_text())
        self.assertTrue(report['passed'] and report['synthetic_only'])
        self.assertFalse(report['native_word'] or build['source_integrated'] or build['release_acceptance'])
        self.assertEqual(report['checker_sha256'], sha(ROOT / 'experiments/full-km-followups/identifier_native.py'))
        self.assertEqual(report['packages']['after'], {lang: build['sha256'][lang + '.zip'] for lang in ['english', 'chinese']})
        self.assertEqual(build['translation_delta']['retained'], 767)
        self.assertEqual(build['translation_delta']['total'], 773)
        self.assertEqual(build['checks'], {'english': 240, 'chinese': 240})

    def test_actual_pdfs_reproduce_then_fix_type_value_split(self):
        for language in ['english', 'chinese']:
            old = locations(ARCHIVE / 'native' / (language + '-boundary-before.pdf'))
            new = locations(ARCHIVE / 'native' / (language + '-boundary-after.pdf'))
            a, b = old.values(); self.assertNotEqual(a[0], b[0])
            a, b = new.values(); self.assertEqual(a[:2], b[:2])
            self.assertEqual(locations(ARCHIVE / 'native' / (language + '-authored-before.pdf')),
                             locations(ARCHIVE / 'native' / (language + '-authored-after.pdf')))


if __name__ == '__main__': unittest.main()
