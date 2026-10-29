from pathlib import Path
import sys,json,csv,math,hashlib,traceback
from datetime import date
from calendar import monthrange
from collections import defaultdict
from statistics import fmean
P=Path(__file__).resolve().parent
ROOT=P.parents[1]; BACK=ROOT/'backend'
sys.path[:0]=[str(BACK),str(BACK/'scripts')]
from run_south_fork_multiyear import parameter_project
from app.services.swat_plus_adapter import SwatPlusAdapter,SwatPlusRunConfig
from scientific_core import ValidationEngine
source=BACK/'data/baseline-diagnostic-multiyear-v1/forcing-project'
exe=BACK/'data/baseline-diagnostic-source-build-v1/compile-v4/swatplus-research'
raw=ROOT/'data/raw/usgs/05451210_2000-01-01_2025-12-31.json'
assert hashlib.sha256(exe.read_bytes()).hexdigest()=='56963a6475aa9014a56a6825749d7fc513fce2dd40dcbb0c0b6a5976364a3c9d'
rows=json.loads(raw.read_text())['value']['timeSeries'][0]['values'][0]['value']
groups=defaultdict(list)
for r in rows:
 d=r['dateTime'][:10]
 if '2005-01-01'<=d<='2012-12-31' and r['qualifiers'] in (['A'],['A','e']):
  q=float(r['value'])*0.028316846592
  if q>=0 and math.isfinite(q): groups[d[:7]].append(q)
assert len(groups)==96 and all(len(v)==monthrange(*map(int,k.split('-')))[1] for k,v in groups.items())
obs={k:fmean(v) for k,v in groups.items()}
allrows=[]
for i,(esco,depth) in enumerate(((e,d) for e in [0.01,0.025,0.05] for d in [8.,10.,12.]),1):
 id=f'v2-cal-{i:02}'; settings={'esco':esco,'shallow_flo_min_m':depth,'tile_t_fc_h':6.}
 dest=P/'runs'/id; project=dest/'project'; resultpath=dest/'result.json'
 row={'id':id,**settings}
 try:
  if resultpath.exists(): result=json.loads(resultpath.read_text())
  else:
   parameter_project(source,project,settings)
   config=SwatPlusRunConfig(project,exe,P/'workspaces',date(2005,1,1),date(2012,12,31),5,'MONTHLY','USGS-05451210',id,outlet_unit='153')
   output=SwatPlusAdapter().run(config)
   pred={r['period'][:7]:r['streamflow_m3s'] for r in output.records}
   assert set(pred)==set(obs) and all(math.isfinite(q) and q>=0 for q in pred.values())
   met=ValidationEngine.evaluate([obs[m] for m in sorted(obs)],[pred[m] for m in sorted(obs)])
   result={'settings':settings,'metrics':met,'predictions':pred}
   resultpath.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
  for k in ['rmse','mae','nse','kge','pbias']: row[k]=result['metrics'][k]['value']
  row['status']='OK'; row['error']=''; row['acceptable']=all(row[k] is not None and math.isfinite(row[k]) for k in ['rmse','nse','kge','pbias']) and row['nse']>=0 and abs(row['pbias'])<=30
 except Exception as e:
  row.update(status='ERROR',error=f'{type(e).__name__}: {e}',acceptable=False); traceback.print_exc()
 allrows.append(row)
 with (P/'calibracion.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['id','esco','shallow_flo_min_m','tile_t_fc_h','status','error','rmse','mae','nse','kge','pbias','acceptable','selection']);w.writeheader();w.writerows(allrows)
 print(id,row,flush=True)
ok=[r for r in allrows if r['status']=='OK']; accepted=[r for r in ok if r['acceptable']]
if len(ok)==9:
 winner=min(accepted,key=lambda r:(r['rmse'],-r['kge'],r['id'])) if accepted else min(ok,key=lambda r:(abs(r['pbias']),r['rmse'],r['id']))
 winner['selection']='ACEPTADO menor RMSE' if accepted else 'EXPLORATORIO menor |PBIAS|; ninguno aceptable'
with (P/'calibracion.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['id','esco','shallow_flo_min_m','tile_t_fc_h','status','error','rmse','mae','nse','kge','pbias','acceptable','selection']);w.writeheader();w.writerows(allrows)
