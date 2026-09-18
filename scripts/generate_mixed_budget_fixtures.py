"""Add public mixed-budget stress fixtures without modifying the locked EN tree."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys
import uuid
from artifact_utils import sha


def cases(folder, ids):
    def read(name):
        return {e['path']:e['value'] for e in json.loads((folder/(name+'.events.json')).read_text())}
    base=read('budget-many');long=read('budget-long')
    costs=next(p for p in base if p.endswith(ids['costQUuid']))
    first=costs+'.'+base[costs]['value'][0]
    item=str(uuid.uuid5(uuid.NAMESPACE_URL,'science-europe/mixed-budget/long-9'))
    target=costs+'.'+item
    mixed=copy.deepcopy(base)
    for path,value in long.items():
        if path.startswith(first+'.'):mixed[target+path[len(first):]]=copy.deepcopy(value)
    mixed[target+'.'+ids['costTitleQUuid']]['value']='Extended resource 9' if folder.name=='en' else '延伸用途資源 9'
    mixed[target+'.'+ids['costAmountQUuid']]['value']='900'
    key=target+'.'+ids['costDescriptionQUuid']
    mixed[key]['value']=mixed[key]['value'].replace('BUDGET-PARA-','MIX-LONG-09-PARA-')
    mixed[costs]['value'].append(item)
    result={'mixed-long-last':mixed}
    leading=copy.deepcopy(mixed);leading[costs]['value']=[item]+base[costs]['value']
    result['mixed-long-first']=leading
    middle=copy.deepcopy(mixed);middle[costs]['value']=base[costs]['value'][:4]+[item]+base[costs]['value'][4:]
    result['mixed-long-middle']=middle
    small=copy.deepcopy(middle);keep=base[costs]['value'][:3]+[item]+base[costs]['value'][4:7]
    small[costs]['value']=keep
    for path in list(small):
        if path.startswith(costs+'.') and path[len(costs)+1:].split('.')[0] not in keep:small.pop(path)
    result['mixed-small-groups']=small
    gaps=copy.deepcopy(mixed)
    def drop(index,field):
        prefix=costs+'.'+gaps[costs]['value'][index]+'.'+ids[field]
        for p in list(gaps):
            if p==prefix or p.startswith(prefix+'.'):gaps.pop(p)
    drop(1,'costCurrencyQUuid')  # Row 2 keeps its explicitly answered zero.
    drop(3,'costCoverQUuid')
    drop(5,'costDescriptionQUuid');drop(5,'costAllocationQUuid')
    # The long row also retains its explicit amount when its currency is absent.
    drop(8,'costCurrencyQUuid')
    result['mixed-gaps']=gaps
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--english',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists();sys.path.insert(0,str(a.english.resolve()/'scripts'))
    from generate_pilot_fixtures import IDS
    a.output.mkdir(parents=True);receipt=dict(public_synthetic=True,template_modified=False,inputs={},cases={})
    for locale in ['en','zh-Hant']:
        source=a.english/'fixtures/pilot'/locale;destination=a.output/locale;destination.mkdir()
        recipe=json.loads((source/'budget-many.json').read_text());bundle=(source/recipe['knowledge_model_package_id']).resolve()
        km=a.output/'knowledge-models'/bundle.name;km.parent.mkdir(exist_ok=True)
        if not km.exists():shutil.copy2(bundle,km)
        assert sha(km)==sha(bundle)
        receipt['inputs'][locale]={name:sha(source/name) for name in ['budget-many.json','budget-many.events.json','budget-long.events.json']}
        receipt['inputs'][locale]['knowledge_model_sha256']=sha(bundle)
        for name,replies in cases(source,IDS).items():
            events=[dict(type='SetReplyEvent',uuid=str(uuid.uuid5(uuid.NAMESPACE_URL,'mixed-budget/'+locale+'/'+name+'/'+path)),path=path,value=value)
                    for path,value in sorted(replies.items(),key=lambda v:(v[0].count('.'),v[0]))]
            target=destination/(name+'.events.json');target.write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n')
            selected=dict(recipe,name='Public mixed-budget QA / '+name,events_file=target.name,knowledge_model_package_id='../knowledge-models/'+km.name)
            path=destination/(name+'.json');path.write_text(json.dumps(selected,ensure_ascii=False,indent=2)+'\n')
            receipt['cases'][locale+'/'+name]=dict(events_sha256=sha(target),recipe_sha256=sha(path),reply_count=len(events))
    (a.output/'provenance.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(cases=len(receipt['cases']),output=str(a.output))))


if __name__=='__main__':main()
