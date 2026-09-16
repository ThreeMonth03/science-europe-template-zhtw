"""Exact page text/geometry, links and raster checks for isolated PDF replays."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from artifact_utils import sha


def page_geometry(data):
    root = ET.fromstring(data)
    return [[dict(page.attrib), [dict(word.attrib, text=word.text or '')
        for word in page.findall('.//{*}word')]] for page in root.findall('.//{*}page')]


def fingerprint(pdf):
    boxes = subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-'])
    geometry = page_geometry(boxes)
    urls = subprocess.check_output(['pdfinfo', '-url', str(pdf)])
    fonts = subprocess.check_output(['pdffonts', str(pdf)])
    with tempfile.TemporaryDirectory(prefix='se-replay-pixels-') as folder:
        subprocess.run(['pdftoppm', '-r', '96', '-png', str(pdf), str(Path(folder)/'page')], check=True, capture_output=True)
        pixels = {p.name: sha(p) for p in sorted(Path(folder).glob('page-*.png'))}
    if not geometry or len(pixels) != len(geometry):
        raise ValueError('No pages or incomplete raster output')
    return {'pages': len(geometry), 'word_count': sum(len(p[1]) for p in geometry),
        'geometry_sha256': hashlib.sha256(json.dumps(geometry, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        'urls_sha256': hashlib.sha256(urls).hexdigest(), 'fonts_sha256': hashlib.sha256(fonts).hexdigest(),
        'page_png_sha256': pixels}


def validate_reports(left, right):
    for report in (left, right):
        if not report['completed_without_crash'] or report['probe'] != 'render':
            raise ValueError('Both render replays must finish without a crash')
    for key in ('sequence', 'source_sha256', 'runner_sha256', 'gc_policy'):
        if left[key] != right[key]:
            raise ValueError('Replay conditions differ: '+key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('baseline', 'patched', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    left, right = [json.loads((p/'report.json').read_text()) for p in (args.baseline, args.patched)]
    validate_reports(left, right)
    result = {'selected_checks_passed': False, 'diagnostic_only': True, 'release_acceptance': False,
        'checker_sha256': sha(Path(__file__)), 'baseline_report_sha256': sha(args.baseline/'report.json'),
        'patched_report_sha256': sha(args.patched/'report.json'), 'rows': [],
        'limits': ['Frozen HTML conversion, not native PDF-entry HTML or queue replay',
            '96 dpi raster comparison, not human content or Microsoft Word acceptance',
            'No-crash runs do not prove the historical crash was fixed']}
    try:
        for number, source in enumerate(left['sequence'], 1):
            name = f'sample-{number:03d}.pdf'
            before, after = args.baseline/name, args.patched/name
            a, b = fingerprint(before), fingerprint(after)
            row = {'iteration': number, 'source': source, 'baseline_sha256': sha(before),
                'patched_sha256': sha(after), 'baseline': a, 'patched': b, 'identical': a == b}
            result['rows'].append(row)
            if a != b:
                raise ValueError(f'Output comparison differs: {number} {source}')
            print(json.dumps({'iteration': number, 'source': source, 'pages': a['pages'], 'identical': True}), flush=True)
        result['selected_checks_passed'] = True
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')


if __name__ == '__main__':
    main()
