"""Disposable 0.3.17 spacing diagnosis, not native DSW or release evidence."""
import argparse
import json
from pathlib import Path
import zipfile
from lxml import etree
from artifact_utils import sha

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
LONG = 'html body #q-required-resources .resource-table:has(.answer-detail > :nth-child(12))'
CSS = {
    'baseline': '',
    'long-auto': LONG + ' { break-inside: auto; }',
    'long-auto-short-row': LONG + ' { break-inside: auto; }\n' + LONG
        + ' > tbody > tr:not(:has(.answer-detail > :nth-child(12))) { break-inside: avoid; }',
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    report = {'release_acceptance': False, 'checker_sha256': sha(Path(__file__)), 'sources': {}, 'variants': {}}
    for language in ['english', 'chinese']:
        html = a.source / f'budget-long-{language}.html'
        docx = a.source / f'budget-long-{language}.docx'
        report['sources'][language] = {'html': sha(html), 'docx': sha(docx)}
        original = html.read_text()
        assert original.count('</style>') == 1
        for profile, css in CSS.items():
            target = a.out / f'{profile}-{language}.html'
            target.write_text(original.replace('</style>', css + '\n</style>'))
            report['variants'][target.name] = sha(target)
        with zipfile.ZipFile(docx) as z:
            parts = {n: z.read(n) for n in z.namelist()}
        for padding in [0, 14, 28]:
            root = etree.fromstring(parts['word/styles.xml'])
            style = next(s for s in root if s.get(W + 'styleId') == 'PilotLongBudget')
            assert style.find(W + 'tcPr') is None
            props = etree.Element(W + 'tcPr')
            style.insert(list(style).index(style.find(W + 'tblStylePr')), props)
            margins = etree.SubElement(props, W + 'tcMar')
            for edge in ['top', 'bottom']:
                etree.SubElement(margins, W + edge, attrib={W + 'w': str(padding), W + 'type': 'dxa'})
            target = a.out / f'padding-{padding}-{language}.docx'
            with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
                for name, data in parts.items():
                    z.writestr(name, etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
                               if name == 'word/styles.xml' else data)
            report['variants'][target.name] = sha(target)
    (a.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(a.out)


if __name__ == '__main__':
    main()
