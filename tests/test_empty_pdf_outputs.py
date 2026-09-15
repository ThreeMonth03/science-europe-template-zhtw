import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from check_empty_pdf_outputs import check_pages


class EmptyPagesTests(unittest.TestCase):
    def test_only_empty_chinese_reduces_pages(self):
        check_pages('empty','chinese',4,3)
        check_pages('empty','english',4,4)
        check_pages('partial','chinese',5,5)

    def test_regressions_are_not_accepted(self):
        for args in [('empty','chinese',4,4),('empty','english',4,5),('partial','chinese',5,4),('negative','english',4,5)]:
            with self.subTest(args=args),self.assertRaises(AssertionError):check_pages(*args)
