import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from artifact_utils import sha
from collect_storage_context_review import verify_previews


class StorageContextReviewTests(unittest.TestCase):
    def test_preview_must_be_bound_to_exact_native_input_and_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ['renders','word-preview']:(root/name).mkdir()
            doc=root/'renders/case-english.docx';pdf=root/'word-preview/case-english.pdf'
            doc.write_bytes(b'native input');pdf.write_bytes(b'preview output')
            receipt=root/'word-preview-cases.json'
            receipt.write_text(json.dumps(dict(completed=True,rows=[dict(name='case-english',docx_sha256=sha(doc),preview_sha256=sha(pdf))])))
            verify_previews(root,['case-english'])
            with self.assertRaises(AssertionError):verify_previews(root,['case-english','case-chinese'])
            doc.write_bytes(b'replaced input')
            with self.assertRaises(AssertionError):verify_previews(root,['case-english'])
            doc.write_bytes(b'native input');pdf.write_bytes(b'replaced output')
            with self.assertRaises(AssertionError):verify_previews(root,['case-english'])
