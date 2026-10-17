import sys, unittest, itertools
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from analysis import solve, headroom, scenarios

class AuditTests(unittest.TestCase):
    def test_constant_supply(self):
        for f in (0,.2,.8,1):
            self.assertAlmostEqual(solve(np.ones((2,24))*13,flex=f)['q'],10)
    def test_no_flex(self):
        self.assertAlmostEqual(solve([[2,4,3,5,6,7]],flex=0,block=2,pue=1)['q'],2)
    def test_no_link_export_protection_irrelevant(self):
        ss=scenarios(link=0)
        for s in ss[:3]:
            np.testing.assert_allclose(headroom(s),headroom(s,False))
        # Importer shock without a link is infeasible; do not silently clip.
        with self.assertRaises(ValueError): headroom(ss[3])
    def test_two_bus_reduction_against_independent_lp(self):
        # Exhaust every integer supply pair in this range; separate 3-variable LP.
        for se,si in itertools.product(range(5,10),range(4,8)):
            h=headroom(dict(se=[se],si=[si],he=[5],hi=[4],k=[3],eta=.9))[0]
            # Variables: exporter generation, flow, new facility load.
            r=linprog([0,0,-1],A_ub=[[-1,1,0],[0,-.9,1]],b_ub=[-5,si-4],
                      bounds=[(0,se),(0,3),(0,None)],method='highs')
            self.assertAlmostEqual(h,r.x[2],places=8)
    def test_integer_oracle_one_job(self):
        # Exhaust every integer allocation, independent of the admission LP.
        for H in itertools.product(range(1,4),repeat=3):
            result=solve([H],flex=1,pue=1,block=3,slack=0,burst=3)
            optimum=max(sum(y)/3 for y in itertools.product(*(range(h+1) for h in H)))
            self.assertAlmostEqual(result['q'],optimum)
    def test_deadline_not_daily_energy(self):
        a=solve([[1,1,5,5]],flex=1,pue=1,block=2,slack=0)
        b=solve([[3,3,3,3]],flex=1,pue=1,block=2,slack=0)
        self.assertAlmostEqual(a['q'],1);self.assertAlmostEqual(b['q'],3)
    def test_causal_gap_witness(self):
        # Same first-period headroom; scenario-specific future needs conflict.
        # This checks shared history constraints even if this example has zero gap.
        H=np.array([[4,1,4,1,4,1],[4,4,1,4,1,4]])
        c=solve(H,flex=.6,pue=1,block=2,slack=2)
        p=solve(H,flex=.6,pue=1,block=2,slack=2,causal=False)
        self.assertLessEqual(c['q'],p['q']+1e-8)
        self.assertAlmostEqual(c['flexible'][0][0],c['flexible'][1][0])
    def test_monotonicity(self):
        H=np.array([headroom(s) for s in scenarios()])
        vals=[solve(H,slack=d)['q'] for d in (0,3,6,12)]
        self.assertTrue(all(b>=a-1e-8 for a,b in zip(vals,vals[1:])))
        self.assertGreaterEqual(solve(H+1)['q'],solve(H)['q'])
    def test_fixed_capacity_above_optimum_rejected(self):
        H=np.array([headroom(s) for s in scenarios()]); q=solve(H)['q']
        self.assertFalse(solve(H,fixed_q=q+.01)['success'])

if __name__=='__main__': unittest.main(verbosity=2)
