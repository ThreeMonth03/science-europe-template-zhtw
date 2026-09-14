import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_quality_outputs import check_summary, compare_unchanged, GAPS


class QualityCheckerTests(unittest.TestCase):
    def document(self):
        ids = ['q-how-data', 'q-quality-control', 'q-copyright-ipr', 'q-dm-responsible', 'q-store-backup'] + [f'q-{i}' for i in range(10)]
        return BeautifulSoup(''.join(f'<div class="question" id="{qid}"><h3>{qid}</h3><div class="answer"><p>Retained fact.</p></div></div>' for qid in ids), 'html.parser')

    def test_terminal_period_belongs_to_sentence_not_method(self):
        check_summary('觀測資料：品質管控措施包括校正、檢核。', 'chinese', ['校正', '檢核'], '觀測資料')
        for text in ('觀測資料：品質管控措施包括校正、檢核。。', '觀測資料：品質管控措施包括校正, 檢核。', '觀測資料：品質管控措施包括校正。'):
            with self.assertRaises(AssertionError): check_summary(text, 'chinese', ['校正', '檢核'], '觀測資料')

    def test_unchanged_questions_pass(self):
        self.assertEqual(14, compare_unchanged(self.document(), self.document(), 'english'))

    def test_unrelated_answer_loss_is_rejected(self):
        before, after = self.document(), self.document()
        after.find(id='q-store-backup').p.string = 'Changed fact.'
        with self.assertRaises(AssertionError): compare_unchanged(before, after, 'english')

    def test_q1_outside_quality_tail_cannot_change(self):
        before, after = self.document(), self.document()
        after.find(id='q-how-data').p.string = 'Changed reuse purpose.'
        with self.assertRaises(AssertionError): compare_unchanged(before, after, 'english')

    def test_only_exact_new_empty_section_fallback_is_permitted(self):
        before, after = self.document(), self.document()
        before.find(id='q-copyright-ipr').p.decompose()
        new = after.find(id='q-copyright-ipr').p
        new.string = GAPS['english']['q-copyright-ipr']; new['data-status'] = 'missing-output'
        self.assertEqual(14, compare_unchanged(before, after, 'english'))
        new.string = 'Invented legal conclusion.'
        with self.assertRaises(AssertionError): compare_unchanged(before, after, 'english')
