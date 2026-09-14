"""Style-only A/B rehearsal on a copied DOCX; never alter the source or its content."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from lxml import etree as ET

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def q(name): return f'{{{W}}}{name}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    assert not args.destination.exists(), 'Never overwrite a rehearsal'
    args.destination.mkdir(parents=True)
    with zipfile.ZipFile(args.source) as archive:
        entries = {n: archive.read(n) for n in archive.namelist()}
    report = {'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(), 'release_acceptance': False, 'variants': {}}
    for profile in ['line-only', 'rhythm']:
        styles = ET.fromstring(entries['word/styles.xml'])
        for style in styles.findall(q('style')):
            name = style.find(q('name')).get(q('val'))
            props = style.find(q('pPr'))
            if name not in ['Normal', 'Body Text', 'First Paragraph', 'Compact', 'heading 3', 'heading 4', 'heading 5']: continue
            if props is None: props = ET.SubElement(style, q('pPr'))
            spacing = props.find(q('spacing'))
            if spacing is None: spacing = ET.SubElement(props, q('spacing'))
            if name in ['Normal', 'Body Text', 'First Paragraph', 'Compact']:
                spacing.set(q('line'), '288'); spacing.set(q('lineRule'), 'auto')
            if profile == 'rhythm':
                if name == 'Compact': spacing.set(q('after'), '40')
                if name == 'heading 3': spacing.set(q('after'), '80')
                if name in ['heading 4', 'heading 5']:
                    spacing.set(q('before'), '160'); spacing.set(q('after'), '60')
        target = args.destination / (profile + '.docx')
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in entries.items():
                archive.writestr(name, ET.tostring(styles, xml_declaration=True, encoding='UTF-8', standalone=True) if name == 'word/styles.xml' else data)
        with zipfile.ZipFile(target) as archive:
            assert all(archive.read(n) == data for n, data in entries.items() if n != 'word/styles.xml')
        report['variants'][profile] = {'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'all_non_style_parts_byte_identical': True}
    (args.destination / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(args.destination)


if __name__ == '__main__': main()
