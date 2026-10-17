"""Finite-scenario admission audit. All electrical inputs are constructed, not observations."""
from pathlib import Path
import json, csv
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix

ROOT = Path(__file__).resolve().parents[1]

def edf_feasible(H,q,flex=.8,slack=6,pue=1.3,burst=2,block=6):
    """Independent online earliest-deadline-first feasibility oracle; no LP code."""
    T=len(H); remaining={}; deadlines={}
    for t,h in enumerate(H):
        if t%block==0:
            remaining[t]=flex*q*block
            deadlines[t]=min(T,t+block+slack)
        capacity=min(burst*flex*q,h/pue-(1-flex)*q)
        if capacity < -1e-8: return False
        for r in sorted(remaining,key=lambda r:(deadlines[r],r)):
            amount=min(remaining[r],max(0.,capacity))
            remaining[r]-=amount;capacity-=amount
        if any(deadlines[r]==t+1 and remaining[r]>1e-7 for r in remaining): return False
    return True

def oracle_capacity(H,**kwargs):
    H=np.asarray(H);pue=kwargs.get('pue',1.3)
    lo,hi=0.,min(H.sum(axis=1))/H.shape[1]/pue+1
    for _ in range(45):
        mid=(lo+hi)/2
        if all(edf_feasible(h,mid,**kwargs) for h in H):lo=mid
        else:hi=mid
    return lo

def interval_witness(H,q,flex=.8,slack=6,pue=1.3,burst=2,block=6):
    """Tightest interval among those containing at least one complete job window."""
    best=None
    for s,h in enumerate(H):
      T=len(h); C=np.minimum(burst*flex*q,np.asarray(h)/pue-(1-flex)*q)
      for a in range(T):
       for b in range(a+1,T+1):
        n=sum(a<=r and min(T,r+block+slack)<=b for r in range(0,T,block))
        if not n:continue
        demand=n*block*flex*q;available=float(sum(C[a:b]));margin=available-demand
        if best is None or margin<best['margin']:
            best=dict(scenario=s,start=a,end=b,mandatory_IT_MWh=demand,
                      available_IT_MWh=available,margin=margin)
    return best

def headroom(s, protect_exporter=True):
    """Two-bus transport model, one-hour periods, supply already net of reserves."""
    se, si, he, hi, k = [np.asarray(s[x], dtype=float) for x in ('se','si','he','hi','k')]
    export = np.minimum(k, se - he if protect_exporter else se)
    if (export < 0).any():
        raise ValueError('Exporter baseline not feasible')
    h = si - hi + s['eta'] * export
    if (h < -1e-9).any():
        raise ValueError('Importer baseline not feasible')
    return h

def solve(H, flex=.8, slack=6, pue=1.3, burst=2., causal=True,
          recover=True, block=6, fixed_q=None):
    """Max average IT MW q; all work completes unless recover=False.

    Jobs arrive at block starts, contain flex*q*block IT MWh and can execute
    through min(release+block+slack,T). Aggregate flexible power <= burst*flex*q.
    Histories include current headroom; there are no scenario probabilities.
    """
    H = np.asarray(H, dtype=float)
    if H.ndim == 1: H = H[None,:]
    ns, T = H.shape
    if T % block or not (0 <= flex <= 1) or pue < 1 or burst < 1 or slack < 0:
        raise ValueError('Invalid input')
    # Index 0 is q; only variables in a job's executable window exist.
    keys=[(s,r,t) for s in range(ns) for r in range(0,T,block)
          for t in range(r,min(T,r+block+slack))]
    ix={key:i+1 for i,key in enumerate(keys)}
    n=1+len(keys); ub=[]; ue=[]; eq=[]; ee=[]
    def row(): return {}
    for s in range(ns):
        for t in range(T):
            a={0:pue*(1-flex)}; b={0:-burst*flex}
            for r in range(0,T,block):
                if (s,r,t) in ix:
                    a[ix[s,r,t]]=pue; b[ix[s,r,t]]=1
            ub.extend((a,b)); ue.extend((H[s,t],0))
        if recover:
            for r in range(0,T,block):
                a={0:-flex*block}
                for t in range(r,min(T,r+block+slack)): a[ix[s,r,t]]=1
                eq.append(a); ee.append(0)
    if causal:
        for t in range(T):
            groups={}
            for s in range(ns):
                hist=tuple(H[s,:t+1])
                if hist not in groups: groups[hist]=s; continue
                ref=groups[hist]
                for r in range(0,T,block):
                    if (s,r,t) in ix:
                        eq.append({ix[s,r,t]:1,ix[ref,r,t]:-1}); ee.append(0)
    def matrix(rows):
        a=lil_matrix((len(rows),n))
        for i,r in enumerate(rows):
            for j,v in r.items(): a[i,j]=v
        return a.tocsr()
    A,B=matrix(ub),matrix(eq)
    c=np.zeros(n); c[0]=-1
    bounds=[(fixed_q,fixed_q) if fixed_q is not None else (0,None)]+[(0,None)]*len(keys)
    result=linprog(c,A_ub=A,b_ub=ue,A_eq=B,b_eq=ee,bounds=bounds,method='highs')
    if not result.success: return {'success':False,'status':result.message}
    x=result.x; Y=np.zeros((ns,T)); jobs={}
    for (s,r,t),i in ix.items(): Y[s,t]+=x[i]; jobs[f'{s},{r},{t}']=float(x[i])
    residual=max(float(np.max(A@x-np.array(ue))),
                 float(np.max(np.abs(B@x-np.array(ee)))) if eq else 0,
                 max(0.,-float(x.min())))
    assert residual < 1e-7, residual
    return dict(success=True,q=float(x[0]),flexible=Y.tolist(),jobs=jobs,
                facility=(pue*((1-flex)*x[0]+Y)).tolist(),residual=residual,
                variables=n,inequalities=len(ub),equalities=len(eq))

def scenarios(severity=6, duration=6, link=10):
    """Five transparent stress paths; labels are generic E and I, not countries."""
    T=24; t=np.arange(T)
    base=dict(se=np.full(T,28.),si=np.full(T,18.),he=np.full(T,18.),
              hi=16+1*((t>=18)&(t<22)),k=np.full(T,float(link)),eta=.95)
    result=[]
    for name,start,target in [('normal',None,None),('E-early',6,'se'),
                              ('E-late',12,'se'),('I-early',6,'si'),
                              ('joint-late',12,'both')]:
        s={k:v.copy() if isinstance(v,np.ndarray) else v for k,v in base.items()}
        if target in ('se','both'): s['se'][start:start+duration]-=severity
        if target in ('si','both'): s['si'][start:start+duration]-=min(3,severity/2)
        s['name']=name; result.append(s)
    return result

def serial(s): return {k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in s.items()}

def run():
    out=ROOT/'results'; out.mkdir(exist_ok=True)
    ss=scenarios(); H=np.array([headroom(s) for s in ss]); H_i=np.array([headroom(s,False) for s in ss])
    (ROOT/'data'/'constructed_scenarios.json').write_text(json.dumps([serial(s) for s in ss],indent=2))
    methods={
      'firm_bilateral':solve(H,flex=0),
      'recovery_bilateral':solve(H),
      'discard_bilateral':solve(H,recover=False),
      'recovery_importer_only':solve(H_i),
      'recovery_perfect_foresight':solve(H,causal=False)}
    bound=float(min(H.sum(axis=1))/24/1.3)
    methods['energy_only_bound']={'q':bound}
    (out/'main.json').write_text(json.dumps(methods,indent=2))
    rows=[]
    for severity in (2,4,6):
      for duration in (2,4,6):
       for f in (.2,.4,.6,.8):
        for slack in (0,3,6,12):
         for pue in (1.2,1.4):
          hs=np.array([headroom(s) for s in scenarios(severity,duration)])
          a=solve(hs,flex=f,slack=slack,pue=pue)
          b=solve(hs,flex=f,slack=slack,pue=pue,recover=False)
          c=solve(hs,flex=f,slack=slack,pue=pue,causal=False)
          oracle=oracle_capacity(hs,flex=f,slack=slack,pue=pue)
          assert abs(oracle-a['q'])<1e-6,(oracle,a['q'])
          rows.append(dict(severity=severity,duration=duration,flex=f,slack=slack,pue=pue,
                           recovery=a['q'],discard=b['q'],foresight=c['q'],
                           oracle_error=abs(oracle-a['q']),
                           max_residual=max(a['residual'],b['residual'],c['residual'])))
    with (out/'sensitivity.csv').open('w') as fp:
        w=csv.DictWriter(fp,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    summary=dict(configurations=len(rows),solves=3*len(rows)+5,
                 max_residual=max(r['max_residual'] for r in rows),
                 max_oracle_error=max(r['oracle_error'] for r in rows),
                 discard_overstatement_min=min(r['discard']/r['recovery']-1 for r in rows),
                 discard_overstatement_max=max(r['discard']/r['recovery']-1 for r in rows),
                 discard_overstates=sum(r['discard']>r['recovery']+1e-7 for r in rows),
                 foresight_overstates=sum(r['foresight']>r['recovery']+1e-7 for r in rows),
                 max_foresight_overstatement=max(r['foresight']/r['recovery']-1 for r in rows))
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    (out/'binding_witness.json').write_text(json.dumps(interval_witness(H,methods['recovery_bilateral']['q']),indent=2))
    print(json.dumps({k:round(v['q'],6) for k,v in methods.items()},indent=2))
    print(json.dumps(summary,indent=2))

if __name__=='__main__': run()
