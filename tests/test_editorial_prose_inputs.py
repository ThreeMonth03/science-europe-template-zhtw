"""Small canonical-input guards; rendered layout and naturalness need human QA."""
import itertools
import re
import unittest
from pathlib import Path

TREE = Path(__file__).resolve().parents[1] / 'translation/tree/src/questions'
LABELS = {
    'findability': '資料搜尋與發現',
    'accessibility': '資料取用',
    'interoperability': '資料互通',
    'reusability': '資料再利用',
    'management': '資料管理',
}
WRAPPERS = {
    1: ('This resource supports {projectCostItemAllocations_0} of data.',
        '支援工作：{projectCostItemAllocations_0}。'),
    2: ('This resource supports {projectCostItemAllocations_0} and {projectCostItemAllocations_1} of data.',
        '支援工作：{projectCostItemAllocations_0}、{projectCostItemAllocations_1}。'),
    3: ('This resource supports {projectCostItemAllocations_0_minus_1}, and {projectCostItemAllocations_minus_1} of data.',
        '支援工作：{projectCostItemAllocations_0_minus_1}、{projectCostItemAllocations_minus_1}。'),
}


def units(question):
    result = {}
    for path in (TREE / question).rglob('translation.md'):
        text = path.read_text()
        source = re.search(r'### Sentence \(en\)\n\n```text\n(.*?)\n```', text, re.S)[1]
        target = re.search(r'### Translation \(zh_Hant\)\n\n~~~jinja\n(.*?)\n~~~', text, re.S)[1]
        result.setdefault(source, []).append(target)
    return result


def canonical(values, source):
    assert len(values[source]) == 1, f'Expected one canonical unit for {source}'
    return values[source][0]


class EditorialProseInputTests(unittest.TestCase):
    def test_fair_work_labels_and_three_wrappers_are_registered_inputs(self):
        values = units('15-required-resources.html.j2')
        for source, target in LABELS.items():
            self.assertEqual(target, canonical(values, source))
        for source, target in WRAPPERS.values():
            self.assertEqual(target, canonical(values, source))
            self.assertEqual(re.findall(r'\{[^}]+\}', source), re.findall(r'\{[^}]+\}', target))

    def test_all_31_nonempty_lists_keep_labels_and_compact_punctuation(self):
        values = units('15-required-resources.html.j2')
        labels = [canonical(values, name) for name in LABELS]
        for mask in itertools.product((False, True), repeat=5):
            selected = [label for label, enabled in zip(labels, mask) if enabled]
            if not selected:
                continue  # No wrapper is used; render checks cover the empty branch.
            count = min(len(selected), 3)
            wrapper = canonical(values, WRAPPERS[count][0])
            fields = dict(projectCostItemAllocations_0=selected[0])
            if count == 2:
                fields['projectCostItemAllocations_1'] = selected[1]
            elif count == 3:
                fields.update(projectCostItemAllocations_0_minus_1='、'.join(selected[:-1]),
                              projectCostItemAllocations_minus_1=selected[-1])
            sentence = wrapper.format_map(fields)
            self.assertEqual('支援工作：' + '、'.join(selected) + '。', sentence)
            self.assertNotRegex(sentence, r'確保|保證|[，,]|及|這項資源支援以下工作')
        self.assertLess(len('支援工作：資料搜尋與發現、資料管理。'),
                        len('這項資源支援以下工作：讓資料更容易被找到及資料管理。'))

    def test_fixed_prepaid_period_stays_unspecified(self):
        source = 'This data set will be kept available for a fixed period (prepaid).'
        target = canonical(units('11-data-preservation.html.j2'), source)
        self.assertEqual('此資料集將在預付費用涵蓋的固定期間內持續提供。', target)
        self.assertNotRegex(target, r'\d|永久|無限期')

    def test_missing_software_hint_does_not_repeat_the_answer(self):
        source = 'Software is required, but the tools have not yet been listed.'
        target = canonical(units('12-access-data.html.j2'), source)
        self.assertEqual('尚待補充：所需軟體的名稱。', target)
        self.assertNotIn('使用此資料集需要特定軟體', target)


if __name__ == '__main__':
    unittest.main()
