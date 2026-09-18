import json
from pathlib import Path
import sys
import tempfile
import unittest
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT/'reviews/2026-09-18-short-resource-rows/reproduce/english'
sys.path[:0]=[str(ROOT/'scripts'),str(FROZEN/'scripts')]
# The archived helper is immutable evidence; importing it must not add a .pyc.
previous_bytecode_setting=sys.dont_write_bytecode
try:
    sys.dont_write_bytecode=True
    import short_resource_rows_contract
finally:
    sys.dont_write_bytecode=previous_bytecode_setting
from artifact_utils import sha
from generate_mixed_budget_fixtures import cases
from mixed_budget_trial import matrix,fragments,trial
from rehearse_mixed_budget import content


class MixedBudgetTrialTests(unittest.TestCase):
    def test_positions_and_group_bounds_change_only_row_opening_attributes(self):
        rows=matrix(FROZEN)
        self.assertEqual([len(r['selected']) for r in rows],[8,8,8,0,31,31,31,0])
        for row in rows:
            before=BeautifulSoup(row['before'],'html.parser');after=BeautifulSoup(row['after'],'html.parser')
            self.assertEqual([str(t) for t in before.select('.pdf-resource-reading')],[str(t) for t in after.select('.pdf-resource-reading')])
            if not row['selected']:self.assertEqual(row['before'],row['after'])
        # A normal non-mixed table must never be changed by this rehearsal path.
        ordinary=str(BeautifulSoup(rows[0]['before'],'html.parser').select('.resource-table')[-1])
        self.assertEqual(trial(ordinary,FROZEN),(ordinary,[]))

    def test_fragment_extraction_rejects_unowned_body_and_nested_tables(self):
        source=matrix(FROZEN)[0]['before']
        table=str(BeautifulSoup(source,'html.parser').select('.resource-table')[-1])
        for bad in [table.replace('<tbody>','<tbody>Unowned'),table.replace('Keep original files.','<table><tr><td>Original</td></tr></table>')]:
            with self.assertRaises(AssertionError):fragments(bad)

    def test_generator_preserves_other_questions_and_zero_with_missing_currency(self):
        ids={name:field for name,field in [('costQUuid','costs'),('costTitleQUuid','title'),('costAmountQUuid','amount'),
            ('costDescriptionQUuid','purpose'),('costCurrencyQUuid','currency'),('costCoverQUuid','funding'),('costAllocationQUuid','activities')]}
        items=['item-'+str(i) for i in range(8)];base={'plan.costs':{'type':'ItemListReply','value':items},'unrelated':{'type':'StringReply','value':'Retain EXACT.csv'}}
        for n,item in enumerate(items):
            for field,value in [('title','Resource '+str(n)),('amount','0' if n==1 else '5000'),('purpose','Short.'),('currency','TWD'),('funding','Institute.'),('activities','FAIR.')]:
                base['plan.costs.'+item+'.'+field]={'type':'StringReply','value':value}
        long=json.loads(json.dumps(base));long['plan.costs.item-0.purpose']['value']='BUDGET-PARA-01: Original.'
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'en';folder.mkdir()
            for name,values in [('budget-many',base),('budget-long',long)]:
                (folder/(name+'.events.json')).write_text(json.dumps([dict(path=p,value=v) for p,v in values.items()]))
            variants=cases(folder,ids)
        self.assertEqual(len(variants),5)
        for row in variants.values():self.assertEqual(row['unrelated'],base['unrelated'])
        gaps=variants['mixed-gaps'];last=gaps['plan.costs']['value'][-1]
        self.assertEqual(gaps['plan.costs.item-1.amount']['value'],'0')
        for key in ['plan.costs.item-1.currency','plan.costs.item-3.funding','plan.costs.item-5.purpose','plan.costs.item-5.activities','plan.costs.'+last+'.currency']:
            self.assertNotIn(key,gaps)
        self.assertEqual(gaps['plan.costs.'+last+'.amount']['value'],'900')
        small=variants['mixed-small-groups'];allowed=small['plan.costs']['value'];self.assertEqual(len(allowed),7)
        self.assertTrue(all(p.split('.')[2] in allowed for p in small if p.startswith('plan.costs.')))

    def test_tracked_public_recipe_and_event_hashes_are_bound(self):
        folder=ROOT/'experiments/mixed-budget/fixtures';proof=json.loads((folder/'provenance.json').read_text())
        self.assertTrue(proof['public_synthetic']);self.assertFalse(proof['template_modified']);self.assertEqual(len(proof['cases']),10)
        for name,row in proof['cases'].items():
            recipe=folder/(name+'.json');data=json.loads(recipe.read_text());events=recipe.parent/data['events_file']
            self.assertEqual(sha(recipe),row['recipe_sha256']);self.assertEqual(sha(events),row['events_sha256'])
            self.assertEqual(len(json.loads(events.read_text())),row['reply_count'])
            self.assertEqual(data['visibility'],'PrivateProjectVisibility')


if __name__=='__main__':unittest.main()
