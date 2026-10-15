import json
from pathlib import Path
import sys
import tempfile
import unittest

import polib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from refresh_po import refresh


class RefreshPOTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.english = self.root / 'english'
        (self.english / 'src').mkdir(parents=True)
        (self.english / 'template.json').write_text(json.dumps(dict(
            organizationId='example', templateId='shared', version='0.7.2', language='en')))
        self.source = self.english / 'src/question.html.j2'
        self.source.write_text("{{ pgettext('ctx', 'Hello') }}")
        self.po_path = self.root / 'zh-Hant.po'
        self.output = self.root / 'review'
        self.save([polib.POEntry(msgctxt='ctx', msgid='Hello', msgstr='你好')])

    def save(self, entries):
        po = polib.POFile()
        po.metadata = {'Language': 'zh-Hant', 'Content-Type': 'text/plain; charset=UTF-8',
                       'Last-Translator': 'Human reviewer', 'X-Review': 'Do not replace'}
        po.extend(entries)
        self.po_path.write_bytes((str(po) + '\n\n').encode())
        return self.po_path.read_bytes()

    def test_noop_preserves_original_bytes_headers_obsolete_and_actual_source_metadata(self):
        raw = self.save([polib.POEntry(msgctxt='ctx', msgid='Hello', msgstr='你好'),
                         polib.POEntry(msgctxt='old', msgid='Retired', msgstr='原譯文', obsolete=True)])
        report = refresh(self.english, self.po_path)
        self.assertFalse(report['accepted'] or report['needs_review'])
        self.assertFalse(self.output.exists())
        refresh(self.english, self.po_path, self.output)
        self.assertEqual(raw, self.po_path.read_bytes())
        self.assertEqual(raw, (self.output / 'zh-Hant.review.po').read_bytes())
        pot = (self.output / 'template.pot').read_text()
        self.assertIn('example:shared:0.7.2', pot)
        self.assertNotIn('0.3.78', pot)
        self.assertEqual(report, json.loads((self.output / 'report.json').read_text()))

    def test_exact_context_merge_preserves_fuzzy_and_never_approves_obsolete_revival(self):
        raw = self.save([polib.POEntry(msgctxt='a', msgid='Same', msgstr='甲', flags=['fuzzy'], tcomment='Human note'),
                         polib.POEntry(msgctxt='b', msgid='Same', msgstr='乙'),
                         polib.POEntry(msgctxt='ctx', msgid='Gone', msgstr='移除的回答'),
                         polib.POEntry(msgctxt='ctx', msgid='Return', msgstr='舊核准譯文', obsolete=True)])
        self.source.write_text("{{ pgettext('a', 'Same') }}{{ pgettext('b', 'Same') }}"
                               "{{ pgettext('c', 'Same') }}{{ pgettext('ctx', 'Return') }}")
        report = refresh(self.english, self.po_path, self.output)
        candidate = polib.pofile(str(self.output / 'zh-Hant.review.po'))
        live = {(e.msgctxt, e.msgid): e for e in candidate if not e.obsolete}
        self.assertEqual('甲', live['a', 'Same'].msgstr)
        self.assertIn('fuzzy', live['a', 'Same'].flags)
        self.assertEqual('Human note', live['a', 'Same'].tcomment)
        self.assertEqual('乙', live['b', 'Same'].msgstr)
        self.assertEqual('', live['c', 'Same'].msgstr)
        self.assertEqual('', live['ctx', 'Return'].msgstr)
        self.assertEqual({('Gone', '移除的回答'), ('Return', '舊核准譯文')},
                         {(e.msgid, e.msgstr) for e in candidate if e.obsolete})
        self.assertEqual(polib.pofile(raw.decode()).metadata, candidate.metadata)
        self.assertEqual(raw, self.po_path.read_bytes())
        self.assertTrue(report['needs_review'])
        self.assertFalse(report['accepted'])
        self.assertEqual((2, 1, 1, 2), (len(report['added']), len(report['removed']), report['fuzzy'], report['untranslated']))

    def test_failed_parse_cannot_write_partial_pot_or_review_directory(self):
        self.source.write_text('{{ pgettext(')
        with self.assertRaisesRegex(ValueError, 'Incomplete POT extraction'):
            refresh(self.english, self.po_path, self.output)
        self.assertFalse(self.output.exists())

    def test_ambiguous_duplicate_and_plural_keys_are_rejected(self):
        entries = [
            [polib.POEntry(msgctxt='ctx', msgid='Hello', msgstr='甲'), polib.POEntry(msgctxt='ctx', msgid='Hello', msgstr='乙')],
            [polib.POEntry(msgctxt='', msgid='Hello', msgstr='甲')],
            [polib.POEntry(msgctxt='ctx\x04alias', msgid='Hello', msgstr='甲')],
            [polib.POEntry(msgid='One', msgid_plural='Many', msgstr_plural={0: '一', 1: '多'})],
        ]
        for values in entries:
            with self.subTest(values=values):
                self.save(values)
                with self.assertRaises(ValueError): refresh(self.english, self.po_path, self.output)
                self.assertFalse(self.output.exists())
        self.save([polib.POEntry(msgctxt='ctx', msgid='Hello', msgstr='你好')])
        self.source.write_text("{{ ngettext('One', 'Many', 2) }}")
        with self.assertRaisesRegex(ValueError, 'plural'): refresh(self.english, self.po_path)

    def test_named_parameters_multiplicity_and_percent_escaping_remain_strict(self):
        for msgid, msgstr in [('Value %(amount)s', '值 %(other)s'),
                             ('%(x)s %(x)s', '%(x)s'), ('Progress 100%', '進度100%')]:
            with self.subTest(msgid=msgid):
                self.source.write_text('{{ pgettext("ctx", ' + json.dumps(msgid) + ') }}')
                self.save([polib.POEntry(msgctxt='ctx', msgid=msgid, msgstr=msgstr)])
                with self.assertRaises(ValueError): refresh(self.english, self.po_path, self.output)
                self.assertFalse(self.output.exists())
        self.source.write_text('{{ pgettext("ctx", "Value %(amount)s / %%") }}')
        raw = self.save([polib.POEntry(msgctxt='ctx', msgid='Value %(amount)s / %%', msgstr='值 %(amount)s / %%')])
        self.assertFalse(refresh(self.english, self.po_path)['needs_review'])
        self.assertEqual(raw, self.po_path.read_bytes())

    def test_existing_output_and_authoritative_po_paths_are_never_overwritten(self):
        raw = self.po_path.read_bytes()
        self.output.mkdir()
        sentinel = self.output / 'keep.txt'
        sentinel.write_text('Keep this existing draft')
        for target in (self.output, self.po_path):
            with self.assertRaises(FileExistsError): refresh(self.english, self.po_path, target)
        self.assertEqual('Keep this existing draft', sentinel.read_text())
        self.assertEqual(raw, self.po_path.read_bytes())


if __name__ == '__main__':
    unittest.main()
