import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import polib
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import refresh_po
from refresh_po import refresh


class RefreshPOTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.pot_path = self.root / 'template.pot'
        self.pipeline_path = self.root / 'pipeline.yml'
        self.commit = 'a' * 40
        self.pipeline = {'source': {
            'repository': 'https://github.com/example/shared.git',
            'organization_id': 'example', 'template_id': 'shared',
            'version': '0.7.2', 'commit': self.commit}}
        self.pipeline_path.write_text(yaml.safe_dump(self.pipeline))
        self.po_path = self.root / 'zh-Hant.po'
        self.output = self.root / 'review'
        self.save_pot([polib.POEntry(msgctxt='ctx', msgid='Hello')])
        self.save([polib.POEntry(msgctxt='ctx', msgid='Hello', msgstr='你好')])

    def refresh(self, output=None):
        return refresh(self.pot_path, self.po_path, output, self.pipeline_path)

    def save_pot(self, entries, headers=None):
        pot = polib.POFile()
        pot.metadata = {'Language': 'en', 'Content-Type': 'text/plain; charset=UTF-8',
                        'X-DSW-Template': 'example:shared:0.7.2',
                        'X-DSW-Source-Commit': self.commit}
        if headers is not None:
            pot.metadata = headers
        pot.extend(entries)
        self.pot_path.write_bytes((str(pot) + '\n\n').encode('utf-8'))
        return self.pot_path.read_bytes()

    def save(self, entries):
        po = polib.POFile()
        po.metadata = {'Language': 'zh-Hant', 'Content-Type': 'text/plain; charset=UTF-8',
                       'Last-Translator': 'Human reviewer', 'X-Review': 'Do not replace'}
        po.extend(entries)
        self.po_path.write_bytes((str(po) + '\n\n').encode('utf-8'))
        return self.po_path.read_bytes()

    def test_noop_preserves_original_and_input_pot_bytes_headers_and_obsolete(self):
        raw = self.save([polib.POEntry(msgctxt='ctx', msgid='Hello', msgstr='你好'),
                         polib.POEntry(msgctxt='old', msgid='Retired', msgstr='原譯文', obsolete=True)])
        pot_raw = self.pot_path.read_bytes()
        report = self.refresh()
        self.assertFalse(report['accepted'] or report['needs_review'])
        self.assertEqual('example:shared:0.7.2', report['source'])
        self.assertEqual(self.commit, report['source_commit'])
        self.assertFalse(self.output.exists())
        self.refresh(self.output)
        self.assertEqual(raw, self.po_path.read_bytes())
        self.assertEqual(raw, (self.output / 'zh-Hant.review.po').read_bytes())
        self.assertEqual(pot_raw, (self.output / 'template.pot').read_bytes())
        self.assertEqual(report, json.loads((self.output / 'report.json').read_text()))

    def test_exact_context_merge_preserves_fuzzy_and_never_approves_obsolete_revival(self):
        raw = self.save([polib.POEntry(msgctxt='a', msgid='Same', msgstr='甲', flags=['fuzzy'], tcomment='Human note'),
                         polib.POEntry(msgctxt='b', msgid='Same', msgstr='乙'),
                         polib.POEntry(msgctxt='ctx', msgid='Gone', msgstr='移除的回答'),
                         polib.POEntry(msgctxt='ctx', msgid='Return', msgstr='舊核准譯文', obsolete=True)])
        self.save_pot([polib.POEntry(msgctxt=context, msgid=message) for context, message in
                       [('a', 'Same'), ('b', 'Same'), ('c', 'Same'), ('ctx', 'Return')]])
        report = self.refresh(self.output)
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

    def test_source_provenance_is_required_and_exact_before_any_output(self):
        baseline = polib.pofile(str(self.pot_path)).metadata
        for header in ('Language', 'X-DSW-Template', 'X-DSW-Source-Commit'):
            for value in (None, '', 'unrelated-source'):
                with self.subTest(header=header, value=value):
                    headers = dict(baseline)
                    if value is None:
                        del headers[header]
                    else:
                        headers[header] = value
                    self.save_pot([polib.POEntry(msgctxt='ctx', msgid='Hello')], headers)
                    with self.assertRaisesRegex(ValueError, 'POT ' + header):
                        self.refresh(self.output)
                    self.assertFalse(self.output.exists())
        self.save_pot([polib.POEntry(msgctxt='ctx', msgid='Hello')],
                      dict(baseline, **{'X-DSW-Source-Commit': 'b' * 40}))
        with self.assertRaisesRegex(ValueError, 'X-DSW-Source-Commit'):
            self.refresh(self.output)

    def test_missing_or_unpinned_pipeline_source_is_rejected(self):
        for pipeline in ({}, {'source': {}}, {'source': dict(self.pipeline['source'], commit='main')},
                         {'source': dict(self.pipeline['source'], version=None)}):
            with self.subTest(pipeline=pipeline):
                self.pipeline_path.write_text(yaml.safe_dump(pipeline))
                with self.assertRaisesRegex(ValueError, 'Pipeline source'):
                    self.refresh(self.output)
                self.assertFalse(self.output.exists())

    def test_malformed_empty_translated_and_obsolete_pots_cannot_create_a_review(self):
        for payload in (b'', b'not a catalog', b'\xff', b'msgid "unterminated'):
            with self.subTest(payload=payload):
                self.pot_path.write_bytes(payload)
                with self.assertRaises(ValueError):
                    self.refresh(self.output)
                self.assertFalse(self.output.exists())
        for entries in ([], [polib.POEntry(msgid='Hello', msgstr='Translation')],
                        [polib.POEntry(msgid='Hello', msgstr=' ')],
                        [polib.POEntry(msgid='Hello', obsolete=True)]):
            with self.subTest(entries=entries):
                self.save_pot(entries)
                with self.assertRaises(ValueError):
                    self.refresh(self.output)
                self.assertFalse(self.output.exists())

    def test_ambiguous_duplicate_empty_and_plural_keys_are_rejected_in_both_catalogs(self):
        entries = [
            [polib.POEntry(msgctxt='ctx', msgid='Hello'), polib.POEntry(msgctxt='ctx', msgid='Hello')],
            [polib.POEntry(msgctxt='', msgid='Hello')],
            [polib.POEntry(msgctxt='ctx\x04alias', msgid='Hello')],
            [polib.POEntry(msgctxt='ctx', msgid='Hello\x04alias')],
            [polib.POEntry(msgid='   ')],
            [polib.POEntry(msgid='One', msgid_plural='Many', msgstr_plural={0: '', 1: ''})],
        ]
        for values in entries:
            with self.subTest(values=values):
                self.save_pot(values)
                with self.assertRaises(ValueError):
                    self.refresh(self.output)
                self.assertFalse(self.output.exists())
                self.save_pot([polib.POEntry(msgctxt='ctx', msgid='Hello')])
                self.save(values)
                with self.assertRaises(ValueError):
                    self.refresh(self.output)
                self.assertFalse(self.output.exists())
                self.save([polib.POEntry(msgctxt='ctx', msgid='Hello', msgstr='你好')])

    def test_named_parameters_multiplicity_and_percent_escaping_remain_strict(self):
        for msgid, msgstr in [('Value %(amount)s', '值 %(other)s'),
                             ('%(x)s %(x)s', '%(x)s'), ('Progress 100%', '進度100%')]:
            with self.subTest(msgid=msgid):
                self.save_pot([polib.POEntry(msgctxt='ctx', msgid=msgid)])
                self.save([polib.POEntry(msgctxt='ctx', msgid=msgid, msgstr=msgstr)])
                with self.assertRaises(ValueError):
                    self.refresh(self.output)
                self.assertFalse(self.output.exists())
        message = 'Value %(amount)s / %%'
        self.save_pot([polib.POEntry(msgctxt='ctx', msgid=message)])
        raw = self.save([polib.POEntry(msgctxt='ctx', msgid=message, msgstr='值 %(amount)s / %%')])
        self.assertFalse(self.refresh()['needs_review'])
        self.assertEqual(raw, self.po_path.read_bytes())

    def test_existing_output_authoritative_po_and_symlinks_are_never_overwritten(self):
        raw = self.po_path.read_bytes()
        self.output.mkdir()
        sentinel = self.output / 'keep.txt'
        sentinel.write_text('Keep this existing draft')
        symlink = self.root / 'review-link'
        symlink.symlink_to(self.output, target_is_directory=True)
        for target in (self.output, self.po_path, symlink):
            with self.assertRaises(FileExistsError):
                self.refresh(target)
        self.assertEqual('Keep this existing draft', sentinel.read_text())
        self.assertEqual(raw, self.po_path.read_bytes())

    def test_po_language_is_not_inferred_or_rewritten(self):
        po = polib.pofile(str(self.po_path))
        po.metadata['Language'] = 'en'
        po.save(str(self.po_path))
        with self.assertRaisesRegex(ValueError, 'PO Language'):
            self.refresh(self.output)
        self.assertFalse(self.output.exists())

    def test_entry_point_has_no_english_source_or_dsw_dependency(self):
        source = Path(refresh_po.__file__).read_text()
        self.assertNotIn('dsw.templating', source)
        self.assertNotIn('extract_catalog', source)
        self.assertNotIn('rglob', source)
        result = subprocess.run([sys.executable, refresh_po.__file__, '--help'],
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('--pot', result.stdout)
        self.assertNotIn('--english', result.stdout)
        result = subprocess.run([sys.executable, '-c',
                                 'import runpy, sys; sys.modules["dsw"] = None; '
                                 'runpy.run_path(sys.argv[1], run_name="boundary_import_check")',
                                 refresh_po.__file__], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_cli_read_only_check_exits_nonzero_for_unreviewed_translation(self):
        # The CLI deliberately uses the repository lock, not an arbitrary --pipeline override.
        source = yaml.safe_load((refresh_po.ROOT / 'pipeline.yml').read_text())['source']
        pot = polib.pofile(str(self.pot_path))
        pot.metadata.update({'X-DSW-Template': ':'.join(str(source[key]) for key in
                            ('organization_id', 'template_id', 'version')),
                             'X-DSW-Source-Commit': source['commit']})
        pot.save(str(self.pot_path))
        self.save([polib.POEntry(msgctxt='ctx', msgid='Hello', msgstr='')])
        raw = self.po_path.read_bytes()
        result = subprocess.run([sys.executable, refresh_po.__file__, '--pot', str(self.pot_path),
                                 '--po', str(self.po_path)], capture_output=True, text=True)
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertTrue(json.loads(result.stdout)['needs_review'])
        self.assertEqual(raw, self.po_path.read_bytes())
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
