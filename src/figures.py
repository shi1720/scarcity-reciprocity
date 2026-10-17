from pathlib import Path
import json,csv,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from analysis import headroom,scenarios
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'figures';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                     'axes.spines.right':False,'savefig.dpi':240})
def save(fig,name):
    fig.savefig(OUT/(name+'.png'),bbox_inches='tight',facecolor='white')
    fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight',facecolor='white');plt.close(fig)

fig,ax=plt.subplots(figsize=(8,3.1));ax.set_axis_off()
boxes=[(.01,.54,.25,.33,'EXPORTING SYSTEM','Supply after reserve\nEssential service floor'),
       (.37,.54,.25,.33,'IMPORTING SYSTEM','Essential service floor\nData centre connection'),
       (.72,.54,.26,.33,'COMPUTE TENANTS','Fixed service\nDeferrable jobs + deadlines'),
       (.18,.02,.65,.29,'BILATERAL RECOVERY TEST','Protect both service floors + finish deferred work\nReport the binding recovery interval')]
for x,y,w,h,title,body in boxes:
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.01',facecolor='#eef3f5',edgecolor='#31586b'))
 ax.text(x+w/2,y+h-.065,title,ha='center',va='center',fontsize=9,fontweight='bold',color='#163b50')
 ax.text(x+w/2,y+h/2-.035,body,ha='center',va='center',fontsize=9)
for a,b in [((.27,.71),(.36,.71)),((.63,.71),(.71,.71)),((.14,.52),(.4,.32)),((.85,.52),(.62,.32))]:
 ax.add_patch(FancyArrowPatch(a,b,arrowstyle='->',mutation_scale=13,color='#31586b'))
ax.text(.315,.83,'Power',ha='center',fontsize=9);ax.text(.67,.83,'Service',ha='center',fontsize=9)
save(fig,'01_governance')

main=json.loads((ROOT/'results/main.json').read_text());s=scenarios()[-1]
H=headroom(s);q=main['recovery_bilateral']['q'];Y=np.array(main['recovery_bilateral']['facility'])[-1]
fig,axes=plt.subplots(2,1,figsize=(8,5),gridspec_kw={'height_ratios':[1,1.1]},sharex=True)
t=np.arange(25)
def hours(v):return np.r_[v,v[-1]]
axes[0].step(t,hours(H),where='post',label='Both essential loads protected',color='#186784',lw=2)
axes[0].step(t,hours(headroom(s,False)),where='post',label='Exporter service floor omitted',color='#ad5a42',ls='--')
axes[0].set_ylabel('Facility headroom (MW)');axes[0].legend(fontsize=8,loc='upper left')
axes[1].step(t,hours(H),where='post',color='#186784',lw=2,label='Available facility power')
axes[1].step(t,hours(Y),where='post',color='#4b7e44',lw=1.5,label='Feasible facility schedule')
axes[1].axhline(1.3*q,color='#ad5a42',ls=':',label='Unshifted average demand')
axes[1].axvspan(12,24,alpha=.07,color='#31586b')
axes[1].set_ylabel('Power (MW)');axes[1].set_xlabel('Hour (constructed 24-hour system)')
axes[1].legend(fontsize=8,loc='upper left');axes[1].set_xlim(0,24)
fig.tight_layout();save(fig,'02_recovery')

rows=list(csv.DictReader((ROOT/'results/sensitivity.csv').open()))
fig,axes=plt.subplots(1,2,figsize=(8,3.5))
labels=['Firm\nbilateral','Recovery\nbilateral','Daily energy\nbound','Recovery\nimporter only']
vals=[main[x]['q'] for x in ['firm_bilateral','recovery_bilateral','energy_only_bound','recovery_importer_only']]
axes[0].bar(range(4),vals,color=['#8b9aa3','#186784','#c58a42','#ad5a42'])
axes[0].set_xticks(range(4),labels,fontsize=8);axes[0].set_ylabel('Average admitted IT load (MW)')
for i,v in enumerate(vals):axes[0].text(i,v+.12,f'{v:.2f}',ha='center',fontsize=9)
axes[0].set_ylim(0,8.5)
for f in (.2,.4,.6,.8):
 selected=[r for r in rows if float(r['severity'])==6 and float(r['duration'])==6 and float(r['flex'])==f and float(r['pue'])==1.4]
 axes[1].plot([float(r['slack']) for r in selected],[float(r['recovery']) for r in selected],marker='o',label=f'{int(f*100)}% flexible')
axes[1].set_xlabel('Additional deadline slack (hours)');axes[1].set_ylabel('Average admitted IT load (MW)')
axes[1].legend(fontsize=8);axes[1].set_xticks([0,3,6,12]);fig.tight_layout();save(fig,'03_capacity')
