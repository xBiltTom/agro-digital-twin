#!/usr/bin/env python3
"""Monthly aggregation, four fixed Ridge fits and descriptive paired bootstrap."""
from pathlib import Path
from calendar import monthrange
from collections import defaultdict
from statistics import fmean
import json, math, csv, random
import numpy as np, pandas as pd, joblib
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
P=Path(__file__).resolve().parent;ROOT=P.parents[1];REPO=ROOT.parent
pro=json.loads((REPO/'agro-digital-twin-st/artifacts/south_fork_monthly_residual_v1/protocol.json').read_text());common=pro['common_features']; plant=pro['fspm_features']; assert not set(common+plant)&set(pro['feature_policy']['excluded'])
raw=json.loads((ROOT/'data/raw/usgs/05451210_2000-01-01_2025-12-31.json').read_text())['value']['timeSeries'][0]['values'][0]['value']; obs={}
for r in raw:
 d=r['dateTime'][:10]; q=float(r['value']); qual=r['qualifiers']
 if qual in (['A'],['A','e']) and q>=0 and math.isfinite(q):
  if d in obs: raise ValueError('Duplicate observed date')
  obs[d]=(q*0.028316846592,qual==['A','e'])
rows=[]
for year in range(2013,2026):
 data=json.loads((P/'annual'/f'{year}.json').read_text());part='TRAIN' if year<=2017 else 'VALIDATION' if year<=2020 else 'TEST'
 for variant in (['PRIMARY','EXCLUDE_ESTIMATED'] if part=='TEST' else ['PRIMARY']):
  for arm in ['A','B']:
   daily=data['data'][arm]
   for month in range(1,13):
    ds=[x for x in daily if int(x['day'][5:7])==month]; expected=monthrange(year,month)[1]; assert len(ds)==expected
    paired=[x for x in ds if x['day'] in obs and (variant=='PRIMARY' or not obs[x['day']][1])];eligible=len(paired)/expected>=.9
    f=[x['fspm'] for x in ds];active=[x for x in f if x['active']]; stress=[x['stress'] for x in active if x['stress'] is not None]
    if len(stress)!=len(active): raise ValueError('Missing water stress during active crop')
    row={'month':f'{year}-{month:02}','partition':part,'variant':variant,'arm':arm,'expected_days':expected,'paired_days':len(paired),'eligible':eligible,'estimated_days':sum(obs[x['day']][1] for x in paired),'observed_streamflow_m3s':fmean(obs[x['day']][0] for x in paired) if eligible else np.nan,'physical_streamflow_m3s':fmean(x['q'] for x in paired) if eligible else np.nan,
    'precipitation_mm':sum(x['weather']['precip_mm'] for x in ds),'temperature_c':fmean(x['weather']['temp_c'] for x in ds),'solar_radiation_mj_m2':sum(x['weather']['solar_rad_mj'] for x in ds),'relative_humidity_percent':fmean(x['weather']['rh_percent'] for x in ds),'wind_speed_ms':fmean(x['weather']['wind_speed_ms'] for x in ds),'et_mm':sum(x['et'] for x in ds),'pet_mm':sum(x['pet'] for x in ds),'percolation_mm':sum(x['perco'] for x in ds),'tile_drainage_mm':sum(x['tile'] for x in ds),'runoff_mm':sum(x['runoff'] for x in ds),'soil_water_profile_mm':fmean(x['soil'] for x in ds),
    'fspm_lai':fmean(x['lai'] for x in f),'fspm_root_depth_m':fmean(x['root'] for x in f),'fspm_biomass_g_plant':fmean(x['biomass'] for x in f),'fspm_transpiration_mm':sum(x['transpiration'] for x in f),'fspm_water_stress':fmean(stress) if stress else np.nan,'fspm_active_days':len(active),'fspm_water_stress_available_days':len(stress)}
    rows.append(row)
frame=pd.DataFrame(rows);frame.to_csv(P/'mensual_v2.csv',index=False)
frame['swat_baseline_streamflow_m3s']=frame.physical_streamflow_m3s
m=pd.to_datetime(frame.month+'-01').dt.month;frame['month_sin']=np.sin(2*np.pi*(m-1)/12);frame['month_cos']=np.cos(2*np.pi*(m-1)/12)
frame['fspm_active_fraction']=frame.fspm_active_days/frame.expected_days;frame['fspm_stress_available_fraction']=frame.fspm_water_stress_available_days/frame.expected_days
assert ((frame.fspm_water_stress.notna())==(frame.fspm_water_stress_available_days>0)).all()
frame['fspm_water_stress']=frame.fspm_water_stress.fillna(0)
models={}; preds=[]
train=frame[(frame.arm=='A') & (frame.partition=='TRAIN') & frame.eligible]; clim=train.groupby(train.month.str[-2:]).observed_streamflow_m3s.mean().to_dict()
for arm in ['A','B']:
 d=frame[frame.arm==arm].copy(); tr=d[(d.partition=='TRAIN') & d.eligible];assert len(tr)==60
 x=tr.physical_streamflow_m3s.to_numpy();y=tr.observed_streamflow_m3s.to_numpy();v=np.mean((x-x.mean())**2);slope=max(0.,np.mean((x-x.mean())*(y-y.mean()))/v) if v else 0.;intercept=y.mean()-slope*x.mean()
 for count in [14,21]:
  names=common+(plant if count==21 else []);assert len(names)==count and np.isfinite(tr[names].to_numpy()).all()
  scaler=StandardScaler().fit(tr[names]);model=Ridge(alpha=10).fit(scaler.transform(tr[names]),y-x)
  name=f'{arm}{count}';models[name]=(scaler,model,names);joblib.dump({'scaler':scaler,'model':model,'features':names,'train':'2013-01/2017-12'},P/f'modelo_v2_{name}.joblib')
 for r in d.to_dict('records'):
  q=r['physical_streamflow_m3s']; yes=bool(r['eligible']); vals={arm:q,f'AFFINE_{arm}':max(0,slope*q+intercept) if yes else np.nan}
  for n in [14,21]:
   sc,model,names=models[f'{arm}{n}']; features=pd.DataFrame([{k:r[k] for k in names}]);
   if yes and not np.isfinite(features.to_numpy()).all(): raise ValueError('Nonfinite predictors')
   vals[f'{arm}{n}']=max(0,q+float(model.predict(sc.transform(features))[0])) if yes else np.nan
  if arm=='A':vals['CLIMATOLOGY']=clim[r['month'][-2:]] if yes else np.nan
  for name,v in vals.items():preds.append({'month':r['month'],'partition':r['partition'],'variant':r['variant'],'series':name,'eligible':yes,'observed':r['observed_streamflow_m3s'],'predicted':v})
out=pd.DataFrame(preds).sort_values(['partition','variant','month','series']);out.to_csv(P/'predicciones_v2.csv',index=False)
# Independent formulas also verified by verificar_metricas.py on a copied input filename.
def metrics(y,p):
 y=np.asarray(y);p=np.asarray(p);e=p-y; sy=np.std(y);sp=np.std(p);den=np.sum((y-y.mean())**2)
 r=np.corrcoef(y,p)[0,1] if sy>0 and sp>0 else np.nan
 return {'n':len(y),'rmse':np.sqrt(np.mean(e**2)),'mae':np.mean(abs(e)),'nse':1-np.sum(e**2)/den if den else np.nan,'kge_prime':1-np.sqrt((r-1)**2+(p.mean()/y.mean()-1)**2+((sp/p.mean())/(sy/y.mean())-1)**2) if sy>0 and p.mean()!=0 and y.mean()!=0 else np.nan,'pbias':100*e.sum()/y.sum() if y.sum()!=0 else np.nan}
met=[]
for (part,var,series),g in out.groupby(['partition','variant','series']):
 g=g[g.eligible & g.observed.notna() & g.predicted.notna()];met.append({'partition':part,'variant':var,'series':series,**metrics(g.observed,g.predicted)})
pd.DataFrame(met).to_csv(P/'metricas_v2.csv',index=False)
# Δ effect convention and interaction: (B14-B21) - (A14-A21), RMSE differences.
res=[]; pairs=[('vegetacion_en_A','A14','A21'),('vegetacion_en_B','B14','B21'),('parametrizacion_14','A14','B14'),('parametrizacion_21','A21','B21'),('D_vs_A','A','B21'),('A_vs_B','A','B')]
for variant in ['PRIMARY','EXCLUDE_ESTIMATED']:
 z=out[(out.partition=='TEST')&(out.variant==variant)];w=z.pivot(index='month',columns='series',values='predicted').sort_index();y=z[z.series=='A'].sort_values('month').observed.to_numpy();assert len(y)==60
 mask=np.isfinite(y)&np.isfinite(w[['A','B','A14','A21','B14','B21']].to_numpy()).all(axis=1)
 for block in [3,6,12,24]:
  rng=random.Random(42); indices=[]
  for i in range(2000):
   ix=[]
   while len(ix)<60:
    a=rng.randrange(60);ix.extend((a+j)%60 for j in range(block))
   indices.append(np.array(ix[:60]))
  def effect(ix,name,ref,config):
   ix=ix[mask[ix]]
   if len(ix)==0:return np.nan
   rm=lambda s: np.sqrt(np.mean((w[s].to_numpy()[ix]-y[ix])**2))
   if name=='interaccion':return (rm('B14')-rm('B21'))-(rm('A14')-rm('A21'))
   return rm(ref)-rm(config)
  for name,ref,config in pairs+[('interaccion','','')]:
   v=np.array([effect(ix,name,ref,config) for ix in indices]);v=v[np.isfinite(v)]
   res.append({'variant':variant,'contrast':name,'reference':ref,'configuration':config,'block_months':block,'eligible_months':int(mask.sum()),'delta_rmse':effect(np.arange(60),name,ref,config),'valid_replicates':len(v),'lower_95':np.quantile(v,.025) if len(v) else np.nan,'upper_95':np.quantile(v,.975) if len(v) else np.nan})
pd.DataFrame(res).to_csv(P/'contrastes_v2.csv',index=False)
print('v2 monthly rows',len(frame),'predictions',len(out),'metrics',len(met),'contrasts',len(res))
old=pd.read_csv(P/'metricas_disponibles.csv')
new=pd.DataFrame(met)
mapnames={'A':'A','B':'B','C':'A14','B14':'B14','D':'B21','AFFINE_A':'AFFINE_A','AFFINE_B':'AFFINE_B','CLIMATOLOGY':'CLIMATOLOGY'}
old=old[old.series.isin(mapnames)].copy();old['configuration']=old.series.map(mapnames);old=old.rename(columns={'rmse':'rmse_original','nse':'nse_original','kge_prime':'kge_prime_original','pbias':'pbias_original','n':'n_original'})
new=new.rename(columns={'series':'configuration','rmse':'rmse_v2','nse':'nse_v2','kge_prime':'kge_prime_v2','pbias':'pbias_v2','n':'n_v2'})
old.merge(new,on=['partition','variant','configuration'],how='inner',suffixes=('_original','_v2')).to_csv(P/'comparacion_metricas_v2.csv',index=False)
