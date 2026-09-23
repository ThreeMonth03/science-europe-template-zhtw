"""Public synthetic mutations for the native prose comparator."""
import copy, unittest
from bs4 import BeautifulSoup
import check


def page(sentence, authored='Authored 原文 v1.2. 0 GB.'):
    sections = []
    for section, count in enumerate([2, 2, 2, 3, 4, 2]):
        questions = []
        for q in range(count):
            identity = 'q-how-data' if section == q == 0 else 'q-' + str(section) + '-' + str(q)
            content = '<p>' + sentence + '</p><div class="answer-detail"><p>' + authored + '</p></div>' if section == q == 0 else ''
            questions.append('<div class="question" id="' + identity + '"><h3>Question</h3><div class="answer">' + content + '</div></div>')
        sections.append('<section class="dmp-section">' + ''.join(questions) + '</section>')
    return '<div id="dmp-content">' + ''.join(sections) + '</div>'


class ProjectionTests(unittest.TestCase):
    def test_only_reviewed_prose_allowed_both_languages(self):
        for language, old_key, new_key in [('en', 'old_en', 'en'), ('zh-Hant', 'old_zh', 'zh')]:
            for unit in check.UNITS[:7]:
                a, b = page(unit[old_key]), page(unit[new_key])
                self.assertEqual(sum(check.html_pair(a, b, language, 'submission').values()), 1)
                with self.assertRaises(AssertionError):
                    check.html_pair(a, b.replace('Authored 原文', 'lost answer'), language, 'submission')
                with self.assertRaises(AssertionError):
                    check.html_pair(a, b.replace(unit[new_key], ''), language, 'submission')

    def test_authored_text_identical_to_old_template_is_not_rewritten(self):
        u = check.UNITS[0]
        a = page(u['old_en'], authored=u['old_en'])
        b = page(u['en'], authored=u['old_en'])
        check.html_pair(a, b, 'en', 'review')
        with self.assertRaises(AssertionError): check.html_pair(a, page(u['en'], authored=u['en']), 'en', 'review')

    def test_negative_not_interchangeable_with_missing(self):
        with self.assertRaises(AssertionError):
            check.html_pair(page(check.UNITS[1]['old_en']), page(check.UNITS[2]['en']), 'en', 'review')

    def test_pdf_projection_rejects_duplicate_or_missing_unit(self):
        u = check.UNITS[0]; text = check.compact(u['en'])
        check.pdf_projection(text, 'en', False, {0: 1})
        for value in ['', text + text]:
            with self.assertRaises(AssertionError): check.pdf_projection(value, 'en', False, {0: 1})


if __name__ == '__main__': unittest.main()
