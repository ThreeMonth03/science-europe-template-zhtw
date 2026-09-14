import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_polish_outputs import owned_runs, assert_quantity_lines, main


class PolishCheckTests(unittest.TestCase):
    def test_failed_rerun_cannot_leave_a_stale_success_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('english.zip', 'chinese.zip'):
                (root / name).write_bytes(b'test package')
            path = root / 'polish-report.json'
            path.write_text('{"selected_checks_passed": true}')
            with patch.object(sys, 'argv', ['checker', '--build', directory, '--cases', 'test']), patch('check_polish_outputs.inspect', side_effect=AssertionError('missing paragraph')):
                with self.assertRaises(AssertionError): main()
            report = json.loads(path.read_text())
            self.assertFalse(report['selected_checks_passed'])
            self.assertEqual('missing paragraph', report['failure'])

    def test_joining_stops_at_gap_and_authored_blocks(self):
        soup = BeautifulSoup('<div><p>Access.</p><div class="joined-policy"><p>Repository.</p></div><div class="reading-gap"><p>Missing.</p></div><div class="joined-policy"><p>Date.</p><p>Licence.</p></div><div class="answer-detail"><p>First.</p><p>Second.</p></div></div>', 'html.parser')
        self.assertEqual([['Access.', 'Repository.'], ['Date.', 'Licence.']], owned_runs(soup.div))

    def test_distribution_label_is_not_joined(self):
        soup = BeautifulSoup('<div><p class="answer-lead"><strong>Distribution 2</strong></p><p>Access.</p><div class="joined-policy"><p>Repository.</p></div></div>', 'html.parser')
        self.assertEqual([['Access.', 'Repository.']], owned_runs(soup.div))

    def test_geometry_rejects_split_unit_and_wrong_numeric_prefix(self):
        for lines, ok in [(['0.0001 GB'], True), (['0.0001 GB of data'], True), (['0.0001', 'GB'], False), (['120 GB'], False), (['10.0001 GB'], False)]:
            xml = '<doc><page>' + ''.join('<line><word>'+line+'</word></line>' for line in lines) + '</page></doc>'
            with patch('check_polish_outputs.subprocess.check_output', return_value=xml.encode()):
                if ok: assert_quantity_lines(Path('test.pdf'), ['0.0001\xa0GB'])
                else:
                    with self.assertRaises(AssertionError): assert_quantity_lines(Path('test.pdf'), ['0.0001\xa0GB'])
