import csv, math, sys
from collections import defaultdict
from pathlib import Path
p=Path(__file__).resolve().parent
suffix = '_v2' if '--v2' in sys.argv else '_disponibles'
g=defaultdict(list)
with (p/f'predicciones{suffix}.csv').open() as f:
 for r in csv.DictReader(f):
  if r['eligible']=='True' and r['observed'] and r['predicted']:
   g[(r['partition'],r['variant'],r['series'])].append((float(r['observed']),float(r['predicted'])))
with (p/f'metricas{suffix}.csv').open() as f:
 for r in csv.DictReader(f):
  pairs=g[(r['partition'],r['variant'],r['series'])]; n=len(pairs);y=[a for a,b in pairs];q=[b for a,b in pairs]; ym=sum(y)/n; qm=sum(q)/n
  sy=math.sqrt(sum((a-ym)**2 for a in y)/n);sq=math.sqrt(sum((b-qm)**2 for b in q)/n)
  corr=sum((a-ym)*(b-qm) for a,b in pairs)/(n*sy*sq)
  vals={'n':n,'rmse':math.sqrt(sum((b-a)**2 for a,b in pairs)/n),'mae':sum(abs(b-a) for a,b in pairs)/n,'nse':1-sum((b-a)**2 for a,b in pairs)/sum((a-ym)**2 for a in y),'pbias':100*sum(b-a for a,b in pairs)/sum(y),'kge_prime':1-math.sqrt((corr-1)**2+(qm/ym-1)**2+((sq/qm)/(sy/ym)-1)**2)}
  for k,v in vals.items(): assert math.isclose(float(r[k]),v,rel_tol=1e-10,abs_tol=1e-10),(r['series'],k,r[k],v)
print('Recalculo independiente correcto:',len(g),'filas de métricas.')
