import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_q8_list_continuity import locations


class Q8ListContinuityTests(unittest.TestCase):
    def test_split_label_and_permission_is_failure(self):
        rows = locations(['Q8 Name', 'Permission. Q9'], 'Q8', 'Q9', [('Name', 'Permission.')])
        self.assertFalse(rows[0]['together'])
        self.assertEqual((1, 2), (rows[0]['label_page'], rows[0]['permission_page']))

    def test_same_text_elsewhere_cannot_rescue_q8(self):
        rows = locations(['Name Permission. Q8 Name', 'Permission. Q9 Name Permission.'], 'Q8', 'Q9', [('Name', 'Permission.')])
        self.assertFalse(rows[0]['together'])

    def test_identical_permissions_keep_their_own_dataset_labels(self):
        rows = locations(['Q8 First Permission. Second', 'Permission. Q9'], 'Q8', 'Q9', [('First', 'Permission.'), ('Second', 'Permission.')])
        self.assertEqual([True, False], [r['together'] for r in rows])

    def test_missing_permission_is_not_an_acceptable_layout(self):
        with self.assertRaises(AssertionError): locations(['Q8 Name Q9'], 'Q8', 'Q9', [('Name', 'Permission.')])
