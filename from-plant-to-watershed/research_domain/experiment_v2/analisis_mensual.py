from pathlib import Path
import json, random, math
import numpy as np, pandas as pd, joblib
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
P=Path(__file__).resolve().parent; ROOT=P.parents[1]; PROJ=ROOT.parent
protocol=json.loads((PROJ/'agro-digital-twin-st/artifacts/south_fork_monthly_residual_v1/protocol.json').read_text())
f=protocol['common_features']; forbidden=set(protocol['feature_policy']['excluded']); assert not set(f)&forbidden
train=pd.read_csv(ROOT/'research_domain/multiyear_v1/monthly-ab.csv',dtype={'station_id':str})
test=pd.read_csv(ROOT/'research_domain/test_v1/monthly-ab.csv',dtype={'station_id':str})
origdev=pd.read_csv(PROJ/'agro-digital-twin-st/artifacts/south_fork_monthly_residual_v1/development-predictions.csv',dtype={'station_id':str})
origtest=pd.read_csv(ROOT/'research_domain/test_v1/monthly-predictions.csv',dtype={'station_id':str})
def features(df):
 d=df.copy(); d['swat_baseline_streamflow_m3s']=d.physical_streamflow_m3s
 m=pd.to_datetime(d.month+'-01').dt.month
 d['month_sin']=np.sin(2*np.pi*(m-1)/12);d['month_cos']=np.cos(2*np.pi*(m-1)/12)
 assert np.isfinite(d[f].to_numpy()).all()
 return d[f]
b=train[(train.arm=='B') & (train.partition=='TRAIN')].copy(); assert len(b)==60
sc=StandardScaler().fit(features(b)); model=Ridge(alpha=10).fit(sc.transform(features(b)),b.observed_streamflow_m3s-b.physical_streamflow_m3s)
joblib.dump({'scaler':sc,'model':model,'features':f,'train':'2013-01/2017-12','source_physics':'original B'},P/'modelo_B14.joblib')
records=[]
for part in ['TRAIN','VALIDATION']:
 d=origdev[origdev.partition==part].copy();d['variant']='PRIMARY';d['eligible']=True
 for r in d.itertuples(): records.append((r.month,part,'PRIMARY',r.series,True,r.observed_streamflow_m3s,r.predicted_streamflow_m3s))
 df=train[(train.arm=='B') & (train.partition==part)].copy()
 predictions=np.maximum(0,df.physical_streamflow_m3s.to_numpy()+model.predict(sc.transform(features(df))))
 for r,q in zip(df.itertuples(),predictions): records.append((r.month,part,'PRIMARY','B14',True,r.observed_streamflow_m3s,q))
for r in origtest.itertuples(): records.append((r.month,'TEST',r.variant,r.series,r.eligible,r.observed_streamflow_m3s,r.predicted_streamflow_m3s))
for variant in ['PRIMARY','EXCLUDE_ESTIMATED']:
 df=test[(test.arm=='B') & (test.variant==variant)].copy(); elig=df.eligible.astype(bool)
 preds=np.full(len(df),np.nan);preds[elig]=np.maximum(0,df.loc[elig,'physical_streamflow_m3s'].to_numpy()+model.predict(sc.transform(features(df.loc[elig]))))
 for r,q in zip(df.itertuples(),preds): records.append((r.month,'TEST',variant,'B14',r.eligible,r.observed_streamflow_m3s,q))
out=pd.DataFrame(records,columns=['month','partition','variant','series','eligible','observed','predicted']).sort_values(['partition','variant','month','series']);out.to_csv(P/'predicciones_disponibles.csv',index=False)
def metrics(y,p):
 y=np.asarray(y);p=np.asarray(p);e=p-y; rm=np.sqrt(np.mean(e**2));ma=np.mean(abs(e));den=np.sum((y-y.mean())**2);nse=1-np.sum(e**2)/den if den else np.nan
 sy=np.std(y);sp=np.std(p); r=np.corrcoef(y,p)[0,1] if sy>0 and sp>0 else np.nan
 k=1-np.sqrt((r-1)**2+(p.mean()/y.mean()-1)**2+((sp/p.mean())/(sy/y.mean())-1)**2) if sy>0 and p.mean()!=0 and y.mean()!=0 else np.nan
 return {'n':len(y),'rmse':rm,'mae':ma,'nse':nse,'kge_prime':k,'pbias':100*e.sum()/y.sum() if y.sum()!=0 else np.nan}
met=[]
for (part,var,series),g in out.groupby(['partition','variant','series']):
 g=g[g.eligible & g.observed.notna() & g.predicted.notna()];met.append({'partition':part,'variant':var,'series':series,**metrics(g.observed,g.predicted)})
pd.DataFrame(met).to_csv(P/'metricas_disponibles.csv',index=False)
# All contrasts are descriptive; use common calendar indices and eligibility after sampling.
contrasts=[('A','B'),('A','C'),('B','B14'),('B','D'),('B14','D'),('C','B14'),('A','D')]
res=[]
for variant in ['PRIMARY','EXCLUDE_ESTIMATED']:
 z=out[(out.partition=='TEST') & (out.variant==variant)]; wide=z.pivot(index='month',columns='series',values='predicted').sort_index(); obs=z[z.series=='A'].sort_values('month').observed.to_numpy(); assert len(wide)==60
 for block in [3,6,12,24]:
  rng=random.Random(42);inds=[]
  for _ in range(2000):
   ix=[]
   while len(ix)<60:
    start=rng.randrange(60);ix.extend((start+j)%60 for j in range(block))
   inds.append(np.array(ix[:60]))
  for ref,config in contrasts:
   a=wide[ref].to_numpy();b=wide[config].to_numpy(); mask=np.isfinite(obs)&np.isfinite(a)&np.isfinite(b)
   def delta(idx):
    use=idx[mask[idx]]
    return np.sqrt(np.mean((a[use]-obs[use])**2))-np.sqrt(np.mean((b[use]-obs[use])**2)) if len(use) else np.nan
   point=delta(np.arange(60)); v=np.array([delta(ix) for ix in inds]);v=v[np.isfinite(v)]
   res.append({'variant':variant,'reference':ref,'configuration':config,'block_months':block,'n_eligible':int(mask.sum()),'delta_rmse':point,'valid_replicates':len(v),'lower_95':np.quantile(v,.025) if len(v) else np.nan,'upper_95':np.quantile(v,.975) if len(v) else np.nan})
pd.DataFrame(res).to_csv(P/'contrastes_disponibles.csv',index=False)
print('Wrote predictions, metrics, paired block bootstrap, and B14 model')
