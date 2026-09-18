"""Actual translated Q15 choices: exact owned-pair delta, no authored edits."""
import argparse
import itertools
import json
from pathlib import Path
import sys
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
from markupsafe import Markup
from rehearse_resource_prose import join_html
from artifact_utils import sha


def check(root, english, language):
    sys.path[:0]=[str(english/'scripts'),str(english/'tests')]
    from resource_prose_contract import QUESTION, prior_question
    from generate_pilot_fixtures import IDS,path
    from test_science_europe_contract import reply_path,reply_items,reply_str_value
    source=(root/QUESTION).read_text(); old=prior_question(source); rows=[]
    for escaped in (False,True):
        env=Environment(loader=FileSystemLoader(root),extensions=['jinja2.ext.do'],autoescape=escaped)
        env.filters.update(reply_path=reply_path,reply_items=reply_items,reply_str_value=reply_str_value,markdown=lambda s:Markup(s))
        before=env.overlay(loader=ChoiceLoader([DictLoader({QUESTION:old}),env.loader]))
        wrapper="{% import 'src/uuids.j2' as uuids %}{% include '"+QUESTION+"' %}"
        templates=[e.from_string(wrapper) for e in (before,env)]
        for hw,charges,detail in itertools.product([None,'','unknown','No','Yes'],repeat=3):
            # Third axis includes absent, authored paragraphs, warning-like text,
            # multi-line and link markup; all remain outside the owned join.
            details={None:'','':'<p>Original.csv: 0.</p>','unknown':'<p>尚待補充：原文。  保留！</p>',
                     'No':'<p>First.</p><p>Second.</p>','Yes':'<p><a href="https://example.org">Original.csv</a></p>'}[detail]
            replies={path('adminDetailsCUuid','additionalHWSWQUuid','additionalHWSWYesAUuid','additionalHWSWYesWhatQUuid'):details}
            for value,names,key in [(hw,('adminDetailsCUuid','additionalHWSWQUuid'),'additionalHWSW'),
                                    (charges,('preservingCUuid','repoChargesQUuid'),'repoCharges')]:
                if value is not None:replies[path(*names)]=IDS.get(key+value+'AUuid',value)
            before,after=[t.render(repliesMap=replies) for t in templates]
            expected,selected=join_html(before,language)
            assert selected==(hw=='No' and charges in ('No','Yes')),(language,hw,charges)
            assert after==expected,(language,hw,charges,detail,escaped,'Unexpected rendered byte delta')
            rows.append(dict(hardware=hw,charges=charges,detail=detail,autoescape=escaped,joined=selected))
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--english',type=Path,required=True)
    a=p.parse_args();target=a.build/'resource-prose-translation.json';assert not target.exists()
    rows=[]
    for folder,language in [('en','english'),('translated','chinese')]:
        cases=check(a.build/folder,a.english.resolve(),language)
        rows.append(dict(language=language,cases=cases,checks=len(cases),joined=sum(r['joined'] for r in cases)))
    target.write_text(json.dumps(dict(passed=True,release_acceptance=False,rows=rows,checker_sha256=sha(Path(__file__))),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(passed=True,checks=sum(r['checks'] for r in rows),joined=sum(r['joined'] for r in rows))))


if __name__=='__main__':main()
