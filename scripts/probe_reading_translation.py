"""Local bilingual collector/equipment matrix, independent of the live renderer."""
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
    import test_reading_units as fixture
    count = 0
    who = [None, 'measuredDataWhoExpertsOwnAUuid', 'measuredDataWhoExpertsOutAUuid', 'measuredDataWhoExternalAUuid']
    equipment = [None, 'measuredDataEquipDescribedAUuid', 'measuredDataEquipCareAUuid']
    english = ['', 'This dataset will be collected by experts in the project, with our own equipment.', 'This dataset will be collected by experts in the project, at a specialized infrastructure.', 'This dataset will be collected by an external party.']
    chinese = ['', '此資料集將由計畫內的專家使用自有設備蒐集。', '此資料集將由計畫內的專家利用專業研究設施蒐集。', '此資料集將委由外部單位蒐集。']
    en_equip = ['', 'The equipment is very well described and known.', 'The equipment is less well described or not completely standard, so we will need to take extra care documenting the process.']
    zh_equip = ['', '所用設備已有完整說明，且為研究團隊所熟悉。', '由於設備說明較不完整，或設備並非完全標準化，研究團隊將特別詳實記錄資料蒐集過程。']
    for locale, folder in [('english', 'en'), ('chinese', 'translated')]:
        env = Environment(loader=FileSystemLoader(args.build / folder), extensions=['jinja2.ext.do'])
        env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items, reply_str_value=adapter.reply_str_value, markdown=lambda v: v, any=any)
        env.tests['true'] = lambda v: v is True
        template = env.from_string("{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include 'src/questions/02-what-data.html.j2' %}")
        for i, j in itertools.product(range(4), range(3)):
            soup = BeautifulSoup(template.render(repliesMap=fixture.collection(who[i], equipment[j])), 'html.parser')
            summary = soup.select_one('.collection-summary')
            if i or j:
                expected = ('Data collection for Coastal observations: ' + ' '.join(v for v in [english[i], en_equip[j]] if v) if locale == 'english' else
                            'Coastal observations的蒐集方式：' + chinese[i] + zh_equip[j])
                assert summary.get_text() == expected, (locale, i, j, summary.get_text())
            else:
                assert summary.get_text() == ('Data collection for Coastal observations has not yet been described.' if locale == 'english' else 'Coastal observations的蒐集方式尚待說明。')
            assert bool(soup.select('[data-fact-id="data-collector"][data-status="missing"]')) == (i == 0)
            assert bool(soup.select('[data-fact-id="equipment-documentation"][data-status="missing"]')) == (j == 0)
            assert not summary.select('p, ul, br')
            count += 1
    report = {'passed': True, 'local_branch_language_checks': count, 'release_acceptance': False,
              'scope': '4 collector states × 3 equipment states × EN/ZH; local adapter, not 24 DSW renders',
              'checker_sha256': sha(Path(__file__)),
              'package_sha256': {name: sha(args.build / name) for name in ('english.zip', 'chinese.zip')}}
    (args.build / 'reading-translation-probe.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__': main()
