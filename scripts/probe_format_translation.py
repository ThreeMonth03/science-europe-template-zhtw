"""Exercise translated Q2 decisions offline, without claiming renderer acceptance."""
import argparse
import itertools
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from artifact_utils import sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--english', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.english.resolve() / 'tests'))
    import test_science_europe_contract as adapter
    import test_format_volume as f
    count = 0
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        env = Environment(loader=FileSystemLoader(args.build / folder), extensions=['jinja2.ext.do'])
        env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items, reply_str_value=adapter.reply_str_value, markdown=lambda v: v, any=any)
        env.tests['true'] = lambda v: v is True
        template = env.from_string("{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include 'src/questions/02-what-data.html.j2' %}")
        def render(data): return BeautifulSoup(template.render(repliesMap=data), 'html.parser').select_one('.format-description')
        for data, files, size in f.volume_cases():
            soup = render(data); text = ' '.join(soup.get_text().split())
            assert bool(soup.select('[data-fact-id="format-file-count"]')) == (not bool((files or '').strip()))
            assert bool(soup.select('[data-fact-id="format-file-size"]')) == (not bool((size or '').strip()))
            if (files or '').strip(): assert (f'We expect {files} files in this format.' if language == 'english' else f'此格式的檔案數預計為 {files} 個。') in text
            if (size or '').strip(): assert (f'The estimated average file size is {size} GB.' if language == 'english' else f'每個檔案的平均大小預計為 {size} GB。') in text
            assert 'MyInstrument v1.2 / CSV' in text
            if language == 'chinese':
                assert 'Data format:' not in text and 'has not been' not in text
                assert '資料格式：' in text
            count += 1
        for why, convert in itertools.product([None, 'formatsWhyNSThereIsNoStandardAUuid', 'formatsWhyNSItIsOptimizedAUuid', 'formatsWhyNSAnotherReasonAUuid'], [None, 'formatsConvertLTSuitableYesAUuid', 'formatsConvertLTSuitableNoAUuid']):
            data = f.values(); data[f.STANDARD] = f.IDS['formatsIsStandardNoAUuid']; data[f.ARCHIVE] = f.IDS['formatsIsLTSuitableNoAUuid']
            if why: data[f.WHY] = f.IDS[why]
            if convert: data[f.CONVERT] = f.IDS[convert]
            soup = render(data)
            assert bool(soup.select('[data-fact-id="nonstandard-reason"][data-status="missing"]')) == (why in (None, 'formatsWhyNSAnotherReasonAUuid'))
            assert bool(soup.select('[data-fact-id="format-conversion"]')) == (convert is None)
            assert ('do not plan to convert' if language == 'english' else '未規劃將資料轉換') in soup.get_text() if convert == 'formatsConvertLTSuitableNoAUuid' else True
            count += 1
        data = f.values(); data[f.STANDARD] = f.IDS['formatsIsStandardNoAUuid']; data[f.WHY] = f.IDS['formatsWhyNSAnotherReasonAUuid']; data[f.REASON] = f.AUTHORED
        detail = render(data).select_one('[data-fact-id="nonstandard-reason"][data-status="complete"]')
        detail.select_one('.answer-lead').decompose()
        assert detail.decode_contents().strip() == f.AUTHORED
        count += 1
    report = {'passed': True, 'local_branch_language_checks': count, 'release_acceptance': False,
              'scope': '25 partial/zero volume combinations + 12 nonstandard/conversion decisions + 1 authored block, each EN/ZH; local adapters, not DSW renders',
              'checker_sha256': sha(Path(__file__)), 'fixture_helper_sha256': sha(args.english / 'tests/test_format_volume.py'),
              'package_sha256': {name: sha(args.build / name) for name in ('english.zip', 'chinese.zip')}}
    (args.build / 'format-translation-probe.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__': main()
