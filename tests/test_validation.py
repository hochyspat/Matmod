"""Контрольные расчёты и нарушения различных правил модели."""
import copy
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from src.io import load_instance
from src.validation import validate_plan

class PlanValidationTests(unittest.TestCase):
    def setUp(self):
        self.data = load_instance(ROOT/'instances/01_basic.json')
        self.plan = json.loads((ROOT/'examples/01_basic_plan.json').read_text(encoding='utf-8'))
    def code(self):
        report=validate_plan(self.data,self.plan)
        self.assertFalse(report['valid'])
        self.assertIsNone(report['recomputed_cost'])
        return report['violations'][0]['code']
    def test_manual_plan(self):
        r=validate_plan(self.data,self.plan)
        self.assertTrue(r['accepted']);self.assertEqual(r['recomputed_cost'],20)
        self.assertEqual([x['warehouse_end'] for x in r['trace']],[4,2,0])
        self.assertEqual([x['period_cost'] for x in r['trace']],[12,5,3])
    def test_tight_capacity(self):
        d=load_instance(ROOT/'instances/02_tight_capacity.json')
        p=json.loads((ROOT/'examples/02_tight_capacity_plan.json').read_text(encoding='utf-8'))
        self.assertEqual(validate_plan(d,p)['recomputed_cost'],24)
    def test_capacity_before_outbound(self):
        self.data['capacity']['warehouse']=2
        self.assertEqual(self.code(),'warehouse_capacity')
    def test_capacity_before_demand(self):
        self.data['capacity']['retailer']=1
        self.assertEqual(self.code(),'retailer_capacity')
    def test_transfer_exceeds_stock(self):
        self.plan['orders']=[1,0,0]
        self.assertEqual(self.code(),'insufficient_warehouse_stock')
    def test_shortage(self):
        self.plan['transfers']=[1,2,3]
        self.assertEqual(self.code(),'shortage')
    def test_terminal_stock(self):
        self.plan['orders']=[6,0,1]
        self.assertEqual(self.code(),'terminal_inventory')
    def test_initial_capacity(self):
        self.data['initial_inventory']['warehouse']=7
        self.assertEqual(self.code(),'initial_capacity')
    def test_retailer_holding_and_fixed_charges(self):
        self.plan.update(transfers=[6,0,0],reported_cost=20)
        r=validate_plan(self.data,self.plan)
        self.assertTrue(r['accepted']);self.assertEqual([x['holding_cost'] for x in r['trace']],[8,4,0])
        self.assertEqual([x['ordering_cost'] for x in r['trace']],[8,0,0])
    def test_wrong_reported_cost(self):
        self.plan['reported_cost']=19
        r=validate_plan(self.data,self.plan)
        self.assertTrue(r['valid']);self.assertFalse(r['accepted']);self.assertEqual(r['cost_difference'],-1)
    def test_invalid_actions(self):
        for values in ([2,2],[-1,2,2],[True,2,2],[2.0,2,2]):
            with self.subTest(values=values):
                p=copy.deepcopy(self.plan);p['orders']=values
                with self.assertRaises(ValueError):validate_plan(self.data,p)
    def test_different_instance(self):
        self.plan['instance_id']='other'
        with self.assertRaises(ValueError):validate_plan(self.data,self.plan)
    def test_nonfinite_cost(self):
        self.plan['reported_cost']=float('nan')
        with self.assertRaises(ValueError):validate_plan(self.data,self.plan)
    def test_no_plan_does_not_prove_infeasibility(self):
        self.plan.update(status='infeasible_proven',has_plan=False,orders=None,transfers=None,reported_cost=None)
        r=validate_plan(self.data,self.plan)
        self.assertIsNone(r['valid']);self.assertIsNone(r['accepted'])
    def test_optimality_not_verified(self):
        self.plan['status']='optimal'
        r=validate_plan(self.data,self.plan)
        self.assertTrue(r['accepted']);self.assertFalse(r['optimality_checked'])
    def test_zero_demand_zero_orders(self):
        self.data['demand']=[0,0,0]
        self.plan.update(orders=[0,0,0],transfers=[0,0,0],reported_cost=0)
        self.assertEqual(validate_plan(self.data,self.plan)['recomputed_cost'],0)
    def test_no_mutation(self):
        old=copy.deepcopy((self.data,self.plan))
        validate_plan(self.data,self.plan)
        self.assertEqual(old,(self.data,self.plan))

if __name__=='__main__':unittest.main()
