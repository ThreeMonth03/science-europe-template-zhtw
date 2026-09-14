import sys
import unittest
from unittest.mock import patch
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_reading_outputs import compare_unchanged, authored_lines, locations


class ReadingCheckerTests(unittest.TestCase):
    def source(self):
        return ''.join(f'<div class="question" id="{qid}"><p>Retain answer {i}.</p></div>'
                       for i, qid in enumerate(['q-what-data', 'q-docs-metadata'] + [f'q-{j}' for j in range(13)]))

    def test_only_instrument_section_is_excluded(self):
        before = self.source().replace('<p>Retain answer 0.', '<div><h4>Instrument datasets</h4>Old wording</div><p>Retain answer 0.')
        after = before.replace('Old wording', 'Reviewed wording')
        self.assertEqual(15, compare_unchanged(*[BeautifulSoup(s, 'html.parser') for s in (before, after)]))

    def test_unrelated_q2_and_q3_answer_loss_fails(self):
        for index in (0, 1, 8):
            before = self.source(); after = before.replace(f'Retain answer {index}.', '')
            with self.assertRaises(AssertionError): compare_unchanged(*[BeautifulSoup(s, 'html.parser') for s in (before, after)])

    def test_pdf_paragraph_geometry_rejects_joining_overlap_and_loss(self):
        first = 'Keep v1.2 and station_YYYYMMDD.csv.'
        second = 'This is a separate authored paragraph!'
        def line(text, top): return f'<line yMin="{top}" yMax="{top + 10}"><word>{text}</word></line>'
        for body, valid in [(line(first, 20) + line(second, 40), True), (line(first + second, 20), False), (line(first, 20) + line(second, 25), False), (line(first, 20), False)]:
            with patch('check_reading_outputs.subprocess.check_output', return_value=f'<doc><page>{body}</page></doc>'.encode()):
                if valid: authored_lines(Path('synthetic.pdf'), 'english', 1)
                else:
                    with self.assertRaises(AssertionError): authored_lines(Path('synthetic.pdf'), 'english', 1)

    def test_table_locations_ignore_author_text_outside_question(self):
        text = '處理紀錄\fQ1 標題\n處理紀錄\n來源校驗碼\fQ2 標題\n處理紀錄\fQ11 處理紀錄'
        with patch('check_reading_outputs.subprocess.check_output', return_value=text):
            self.assertEqual({'處理紀錄': [2], '來源校驗碼': [2]}, locations(Path('synthetic.pdf'), ['處理紀錄', '來源校驗碼'], 'Q1 標題', 'Q2 標題'))

    def test_table_locations_preserve_real_splits_and_do_not_rescue_lost_cells(self):
        for text, expected in [
            ('Q1\nProcessing log\fSource checksum\nQ2', {'Processing log': [1], 'Source checksum': [2]}),
            ('Q1\nProcessing log\nQ2\nSource checksum', {'Processing log': [1], 'Source checksum': []}),
        ]:
            with patch('check_reading_outputs.subprocess.check_output', return_value=text):
                self.assertEqual(expected, locations(Path('synthetic.pdf'), ['Processing log', 'Source checksum'], 'Q1', 'Q2'))

    def test_table_locations_fail_closed_on_missing_or_ambiguous_boundaries(self):
        for text in ['Q1 cell', 'Q1 Q1 cell Q2', 'Q2 cell Q1']:
            with patch('check_reading_outputs.subprocess.check_output', return_value=text):
                with self.assertRaises(AssertionError): locations(Path('synthetic.pdf'), ['cell'], 'Q1', 'Q2')
