import sys
import tempfile
import unittest
from pathlib import Path
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from diagnose_word_import_layout import clean_pages, paragraph_spans, q5_labels, same_page, text_comparison, W
from compare_word_preview_engines import image_id


class WordImportLayoutTests(unittest.TestCase):
    def test_engine_tags_and_unverified_images_are_rejected(self):
        with patch('compare_word_preview_engines.subprocess.check_output') as inspect:
            for value in ['latest', 'gotenberg/gotenberg:8', 'sha256:short']:
                with self.assertRaises(ValueError): image_id(value)
            inspect.assert_not_called()
            identity = 'sha256:' + 'a' * 64
            inspect.return_value = identity + '\n'
            self.assertEqual(image_id(identity), identity)
            inspect.return_value = 'sha256:' + 'b' * 64
            with self.assertRaises(ValueError): image_id(identity)

    def test_roundtrip_text_difference_cannot_be_reported_as_preserved(self):
        key = 'full_text_without_whitespace_and_verified_footers_sha256'
        rows = [dict(mode='direct', **{key: 'a'}), dict(mode='same-policy', **{key: 'a'}),
                dict(mode='same-policy-reopened', **{key: 'b'})]
        result = text_comparison(rows)
        self.assertTrue(result['all_memory_exports_same_normalized_text'])
        self.assertFalse(result['all_exports_same_normalized_text'])
        self.assertEqual(result['reopened_text_equals_direct'], {'same-policy-reopened': False})
        rows[1][key] = 'c'
        self.assertFalse(text_comparison(rows)['all_memory_exports_same_normalized_text'])

    def test_complete_paragraph_crossing_pages_is_not_same_page(self):
        spans = paragraph_spans(['Heading.Policy', 'sentence.Intro.Item1.Item2.'],
                                ['Heading.', 'Policy sentence.', 'Intro.', 'Item1.', 'Item2.'])
        self.assertEqual(spans, [[1], [1, 2], [2], [2], [2]])
        self.assertFalse(same_page(spans))
        self.assertTrue(same_page([[2]] * 5))
        self.assertFalse(same_page([]))

    def test_missing_duplicate_and_punctuation_changes_rejected(self):
        for pages in [['Other.'], ['Policy.Policy.'], ['Policy']]:
            with self.assertRaises(ValueError): paragraph_spans(pages, ['Policy.'])
        self.assertEqual(paragraph_spans(['政 策。'], ['政策。']), [[1]])

    def test_only_geometrically_verified_footer_is_removed(self):
        bbox = b'<doc><page height="800"/><page height="800"><line yMin="750"><word>2/2</word></line></page></doc>'
        self.assertEqual(clean_pages('Cover.\fPolicy.\n2/2\f', bbox), ['Cover.', 'Policy.'])
        with self.assertRaises(ValueError): clean_pages('Cover.\fPolicy.\n2/2\n2/2\f', bbox)
        with self.assertRaises(ValueError): clean_pages('Cover.\fPolicy.\n2/2\f', bbox.replace(b'750', b'400'))
        with self.assertRaises(ValueError): clean_pages('Cover.\fPolicy.\n2/2\f', b'<doc><page height="800"/><page height="800"/></doc>')

    def fixture(self, path, styles=None, extra=''):
        styles = styles or ['Heading3', 'PilotLead', 'PilotLead', 'PilotListLead', 'Compact', 'Heading3']
        labels = ['5. Storage?', 'Policy.', 'Limitations:', 'Location missing.', 'Schedule missing.', '6. Security?']
        paragraphs = ''.join(f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>' for style, text in zip(styles, labels))
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('word/document.xml', f'<w:document xmlns:w="{W[1:-1]}"><w:body>{paragraphs}{extra}</w:body></w:document>')

    def test_bounded_fixture_identity_is_required(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'case.docx'
            self.fixture(path)
            self.assertEqual(len(q5_labels(path)), 5)
            self.fixture(path, ['Heading3', 'BodyText', 'PilotLead', 'PilotListLead', 'Compact', 'Heading3'])
            with self.assertRaises(ValueError): q5_labels(path)
            self.fixture(path, extra='<w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr><w:r><w:t>5. Duplicate?</w:t></w:r></w:p>')
            with self.assertRaises(ValueError): q5_labels(path)


if __name__ == '__main__': unittest.main()
