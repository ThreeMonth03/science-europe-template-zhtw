import copy
from pathlib import Path
import sys
import unittest
from jinja2 import Environment, FileSystemLoader, DictLoader, ChoiceLoader
from markupsafe import Markup
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / 'reviews/2026-09-18-short-resource-rows/reproduce/english'
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/mixed-budget-header')]
from compact import compact_source, restore_source
from capture import public_mixed_input
from prototype import patch_budget, project_budget, patch_package, ORDINARY, BODY, TAIL
from check_native_mixed_header import page_bounds


class NativeMixedHeaderTests(unittest.TestCase):
    def test_font_externalization_is_lossless_and_wrong_font_is_rejected(self):
        source = b'<style>a{src:url("data:font/ttf;base64,Zm9udA==")}b{src:url("data:font/ttf;base64,Zm9udA==")}</style><p>KEEP exact.</p>'
        result, fonts = compact_source(source)
        self.assertEqual(len(fonts), 1)
        digest = next(iter(fonts))
        self.assertEqual(fonts[digest], {'bytes': 4, 'occurrences': 2})
        self.assertEqual(restore_source(result, {digest: b'font'}), source)
        with self.assertRaises(AssertionError): restore_source(result, {digest: b'changed'})
        with self.assertRaises(AssertionError): compact_source(result)
        self.assertTrue(result.endswith(b'<p>KEEP exact.</p>'))

    def test_observer_only_accepts_the_marked_public_mixed_fixture(self):
        source = b'<table class="resource-table pdf-resource-reading">' + b''.join(f'MIX-LONG-09-PARA-{n:02d}:'.encode() for n in range(1, 61))
        self.assertTrue(public_mixed_input(source))
        self.assertFalse(public_mixed_input(source.replace(b'MIX-LONG-09-PARA-07:', b'')))
        self.assertFalse(public_mixed_input(source + b'MIX-LONG-09-PARA-07:'))
        self.assertFalse(public_mixed_input(b'An unrelated project'))

    def test_prototype_changes_only_two_owned_sources_and_is_reversible(self):
        source = (FROZEN / 'src/budget-reading.html.j2').read_text()
        self.assertEqual(project_budget(patch_budget(source)), source)
        original = {'version': '0.3.42', 'formats': ['unchanged'], 'assets': ['unchanged'], 'files': [
            {'fileName': 'src/budget-reading.html.j2', 'content': source, 'uuid': 'budget'},
            {'fileName': 'src/layout.css', 'content': 'Keep existing CSS.', 'uuid': 'style'},
            {'fileName': 'src/questions/15-required-resources.html.j2', 'content': 'Keep user content.', 'uuid': 'question'}]}
        before = copy.deepcopy(original)
        result = patch_package(original)
        self.assertEqual(original, before)
        self.assertEqual(result['version'], '0.3.42')
        self.assertEqual(result['files'][2], original['files'][2])
        self.assertEqual(result['files'][1]['content'], 'Keep existing CSS.' + TAIL)
        for invalid in [source.replace(ORDINARY, ''), source + ORDINARY, source.replace(BODY, ''), patch_budget(source)]:
            with self.assertRaises(AssertionError): patch_budget(invalid)

    def test_prototype_retains_short_group_bounds_and_all_long_text(self):
        source = (FROZEN / 'src/budget-reading.html.j2').read_text()
        env = Environment(loader=ChoiceLoader([DictLoader({'src/budget-reading.html.j2': patch_budget(source)}), FileSystemLoader(FROZEN)]),
                          extensions=['jinja2.ext.do'], autoescape=True)
        render = env.get_template('src/budget-reading.html.j2').module.render
        for count, index, expected in [(9, 0, 8), (9, 4, 8), (9, 8, 8), (7, 3, 0), (32, 0, 31), (33, 32, 0)]:
            rows = []
            for n in range(count):
                purpose = '<p>Keep data.</p><p>Support.</p>'
                if n == index:
                    purpose = '<div class="answer-detail" data-fact-id="resource-justification" data-status="complete">' + ''.join(f'<p>LONG-{i}: original text.</p>' for i in range(60)) + '</div><p>Support.</p>'
                row = {'id': f'row-{n}', 'title': Markup(f'<p><strong>Resource {n}</strong></p>'),
                       'purpose': Markup(purpose), 'budget': Markup('<p>0 TWD</p>'), 'funding': Markup('<p>Institute.</p>')}
                row['original'] = Markup(f'<tr data-item-id="row-{n}"><td>{row["title"]}{purpose}</td><td>{row["budget"]}</td><td>{row["funding"]}</td></tr>')
                rows.append(row)
            header = Markup('<tr><th scope="col">Resource</th><th scope="col">Budget</th><th scope="col">Funding</th></tr>')
            original = Markup('<table class="resource-table"><thead>' + header + '</thead><tbody>' + ''.join(r['original'] for r in rows) + '</tbody></table>')
            result = render(original, header, rows)
            soup = BeautifulSoup(result, 'html.parser')
            self.assertEqual(len(soup.select('.pdf-short-resource-row')), expected, (count, index))
            self.assertTrue(all(str(result).count(f'LONG-{i}:') == 1 for i in range(60)))
            if count <= 32:
                self.assertEqual(soup.select_one('.pdf-resource-reading tbody')['style'], 'break-inside: avoid')
            else:
                self.assertEqual(result, original)

    def test_pdf_bounds_detect_actual_clipping_and_footer_intrusion(self):
        source = b'<html><page width="595" height="842"><flow><block><line yMin="100"><word xMin="60" xMax="90" yMin="100" yMax="114">Body</word></line><line yMin="800"><word xMin="280" xMax="310" yMin="800" yMax="811">1/1</word></line></block></flow></page></html>'
        self.assertEqual(page_bounds(source), [])
        for invalid in [source.replace(b'yMin="100" yMax="114"', b'yMin="-1" yMax="114"'), source.replace(b'yMax="114"', b'yMax="795"')]:
            self.assertEqual(len(page_bounds(invalid)), 1)


if __name__ == '__main__':
    unittest.main()
