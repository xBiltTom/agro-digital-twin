"""Validate shared dates/forcing and no missing crop structural states."""
from pathlib import Path
from datetime import date, timedelta
import hashlib,json,math
p=Path(__file__).resolve().parent
contract=hashlib.sha256((p/'frozen_plant_contract_v2.json').read_bytes()).hexdigest()
for year in range(2013,2026):
 d=json.loads((p/'annual'/f'{year}.json').read_text()); assert d['plant_contract_sha256']==contract
 days=[(date(year,1,1)+timedelta(days=i)).isoformat() for i in range((date(year+1,1,1)-date(year,1,1)).days)]
 a,b=d['data']['A'],d['data']['B'];assert [r['day'] for r in a]==[r['day'] for r in b]==days
 assert d['other_inputs_identical'] and d['A_plants_sha256']!=d['B_plants_sha256']
 for x,y in zip(a,b):
  assert x['weather']==y['weather']
  for r in (x,y):
   f=r['fspm'];assert all(math.isfinite(float(f[k])) and float(f[k])>=0 for k in ('lai','root','biomass','transpiration'))
   assert (f['stress'] is not None)==f['active']
   if f['stress'] is not None: assert 0<=f['stress']<=1
   if not f['active']: assert all(f[k]==0 for k in ('lai','root','biomass','transpiration'))
 print(year, len(days), 'dias verificados')
