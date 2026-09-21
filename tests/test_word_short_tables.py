import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
import jinja2
from lxml import etree
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-word-short-tables'
sys.path[:0] = [str(ROOT / 'experiments/word-short-tables'), str(ROOT / 'scripts')]
from table_recipe import HERE, ARCHIVE as PARENT, LUA, XML, WORD_FORMATS, baseline, patch, reverse, sha
from table_probe import inspect, xml_delta, cases
from engine_preview import inspect as inspect_engine_preview
from translation_probe import run as translation_probe


class WordShortTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = jinja2.Environment(autoescape=True, extensions=['jinja2.ext.do', 'jinja2.ext.loopcontrols']).from_string(
            (HERE / 'short-tables.xml.j2').read_text())

    def test_only_two_shared_files_and_word_pipelines_change_reversibly(self):
        for language in ['english', 'chinese']:
            old = baseline(language); new = patch(old, language)
            self.assertEqual(reverse(new, language), old)
            self.assertEqual(new['files'][:-1], old['files']); self.assertEqual(new['assets'][:-1], old['assets'])
            self.assertEqual(new['files'][-1]['fileName'], XML); self.assertEqual(new['assets'][-1]['fileName'], LUA)
            self.assertEqual({k: v for k, v in old.items() if k not in ['files', 'assets', 'formats']},
                             {k: v for k, v in new.items() if k not in ['files', 'assets', 'formats']})
            self.assertEqual([f for f in old['formats'] if f['uuid'] not in WORD_FORMATS],
                             [f for f in new['formats'] if f['uuid'] not in WORD_FORMATS])
            bad = copy.deepcopy(old); bad['files'][0]['content'] += ' '
            with self.assertRaises(AssertionError): patch(bad, language)
            for mutation in ['file', 'step', 'asset']:
                bad = copy.deepcopy(new)
                if mutation == 'file': bad['files'][-1]['content'] += ' '
                elif mutation == 'step': next(f for f in bad['formats'] if f['uuid'] in WORD_FORMATS)['steps'][-1]['options'] = {}
                else: bad['assets'][-1]['uuid'] = 'incorrect'
                with self.assertRaises(AssertionError): reverse(bad, language)
        self.assertEqual(patch(baseline('english'), 'english')['files'][-1]['content'],
                         patch(baseline('chinese'), 'chinese')['files'][-1]['content'])

    def test_no_marker_is_exact_noop_and_marked_xml_matches_actual_engine(self):
        for source in list((PARENT / 'after/renders').glob('*.docx')) + [ARCHIVE / 'engine/before.docx']:
            with zipfile.ZipFile(source) as z: raw = z.read('word/document.xml').decode()
            self.assertEqual(self.template.render(content=raw), raw)
        with zipfile.ZipFile(ARCHIVE / 'engine/marked.docx') as z: marked = z.read('word/document.xml').decode()
        with zipfile.ZipFile(ARCHIVE / 'engine/after.docx') as z: final = z.read('word/document.xml').decode()
        self.assertEqual(self.template.render(content=marked), final)
        self.assertEqual(self.template.render(content=final), final)
        self.assertNotIn('<!--DSW:SE:short-table:', final)

    def test_generated_marker_contract_rejects_unknown_structure_and_never_unescapes_text(self):
        with zipfile.ZipFile(ARCHIVE / 'engine/marked.docx') as z: marked = z.read('word/document.xml').decode()
        begin = '<!--DSW:SE:short-table:v1:begin-->\n    '; end = '\n    <!--DSW:SE:short-table:v1:end-->'
        prefix, tail = marked.split(begin, 1); table, suffix = tail.split(end, 1)
        changes = [
            lambda s: s.replace('PilotTableLead', 'Compact', 1),
            lambda s: s.replace('<w:tr>', '<w:tr><w:trPr><w:cantSplit/></w:trPr>', 1),
            lambda s: s.replace('<w:tcPr', '<w:gridSpan w:val="2"/><w:tcPr', 1),
            lambda s: s.replace('<w:tcPr', '<w:vMerge/><w:tcPr', 1),
            lambda s: s.replace('</w:tc>', '<w:p/></w:tc>', 1),
            lambda s: '<w:tbl>' + s + '</w:tbl>',
            lambda s: s.replace('<w:tr>', '<w:tr><w:tr>', 1),
        ]
        for transform in changes:
            with self.assertRaises(jinja2.UndefinedError): self.template.render(content=prefix + begin + transform(table) + end + suffix)
        for bad in [None, marked.replace(begin, begin.rstrip(), 1), marked.replace(end, '', 1), marked.replace(begin, '', 1)]:
            with self.assertRaises(jinja2.UndefinedError): self.template.render(content=bad)
        raw = '<w:t>&lt;!--DSW:SE:short-table:v1:begin--&gt; &amp; 0 / N/A.</w:t>'
        self.assertEqual(self.template.render(content=raw), raw)

    def test_engine_matrix_reproduces_noop_and_only_fourteen_bounded_table_changes(self):
        report = json.loads((ARCHIVE / 'engine/report.json').read_text())
        self.assertEqual(inspect(ARCHIVE / 'engine'), report['rows'])
        self.assertEqual(len(cases()), 37); self.assertEqual(sum(r['changed_tables'] for r in report['rows']), 14)
        self.assertTrue(report['no_op_all_components_identical']); self.assertFalse(report['native_checked'])
        for name, digest in report['source_sha256'].items(): self.assertEqual(sha((HERE / name).read_bytes()), digest)
        for name, digest in report['artifacts'].items(): self.assertEqual(sha((ARCHIVE / 'engine' / name).read_bytes()), digest)
        rows = {r['case']: r for r in report['rows']}
        for name in ['many-rows', 'multi-paragraph', 'nested-table', 'rowspan', 'colspan', 'other-question',
                     'nested-question-lookalike', 'other-question-lookalike', 'adjacent-tables']:
            self.assertEqual(rows[name]['changed_tables'], 0)
        preview = json.loads((ARCHIVE / 'engine/preview-verified.json').read_text())
        self.assertEqual(json.loads(json.dumps(inspect_engine_preview(ARCHIVE / 'engine'))), preview['rows'])
        self.assertEqual([r['pages'] for r in preview['rows']], [15, 15])

    def test_xml_oracle_rejects_table_text_extra_keep_and_unrelated_paragraph_changes(self):
        with zipfile.ZipFile(ARCHIVE / 'after/renders/ethics-long-review-chinese.docx') as z: after = etree.fromstring(z.read('word/document.xml'))
        with zipfile.ZipFile(PARENT / 'after/renders/ethics-long-review-chinese.docx') as z: before = etree.fromstring(z.read('word/document.xml'))
        for mutation in ['text', 'last-style', 'missing-row-keep', 'outside']:
            broken = copy.deepcopy(after)
            table = next(t for t in broken.iter(qn('w:tbl')) if any(n.text == 'Retained.' for n in t.iter(qn('w:t'))))
            if mutation == 'text': next(n for n in table.iter(qn('w:t')) if n.text == 'Retained.').text = 'Retained!'
            elif mutation == 'last-style': next(table.findall(qn('w:tr'))[-1].iter(qn('w:pStyle'))).set(qn('w:val'), 'PilotTableLead')
            elif mutation == 'missing-row-keep':
                node = next(table.iter(qn('w:cantSplit'))); node.getparent().remove(node)
            else: next(broken.iter(qn('w:t'))).text = 'Changed outside the table.'
            with self.assertRaises(AssertionError): xml_delta(before, broken, 1)

    def test_translation_gap_and_asset_alternative_are_reproduced_without_claiming_integration(self):
        with tempfile.TemporaryDirectory() as temporary:
            for storage in ['jinja', 'asset']:
                frozen = ARCHIVE / 'translation' / storage
                result = translation_probe(frozen / 'source', Path(temporary) / storage, storage)
                self.assertEqual(result, json.loads((frozen / 'report.json').read_text()))
                self.assertTrue(result['minimal_shared_files_probe'])
                self.assertFalse(result['full_source_integration'])
                if storage == 'jinja':
                    self.assertFalse(result['passed']); self.assertTrue(result['integration_blocked'])
                    self.assertEqual(result['translation_units'], 7)
                    self.assertNotEqual(result['source_sha256'][XML], result['expanded_sha256'][XML])
                else:
                    self.assertTrue(result['passed']); self.assertEqual(result['translation_units'], 0)
                    self.assertFalse(result['native_asset_pipeline_checked'])


if __name__ == '__main__': unittest.main()
