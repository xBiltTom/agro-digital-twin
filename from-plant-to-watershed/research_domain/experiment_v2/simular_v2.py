#!/usr/bin/env python3
"""Isolated SWAT+/FSPM v2: derive 2010 contract, then paired annual runs."""
from pathlib import Path
from datetime import date
from statistics import fmean
import sys, json, hashlib, tarfile, shutil, gc, math, csv, traceback, os, tempfile
P=Path(__file__).resolve().parent; ROOT=P.parents[1]; BACK=(ROOT/'backend').resolve()
sys.path[:0]=[str(BACK),str(BACK/'scripts')]
from run_south_fork_multiyear import parameter_project, copy_inputs
from app.services.swat_plus_adapter import SwatPlusAdapter,SwatPlusRunConfig
from app.services.swat_plus_parser import SwatOutputParser
from types import SimpleNamespace
from app.services.swat_coupled_runner import run_coupled_swat_with_executed_calendar, _calendar_from_result
from app.services.swat_executed_calendar import SwatExecutedCropCalendar
from app.services.executed_calendar_fspm import run_fspm_on_executed_calendar
from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader, SwatPlantParameterMapper
from app.schemas.coupling import CouplingPlantParameterSummary
R=BACK/'data'/os.environ.get('SOUTH_FORK_V2_WORK','south-fork-v2-isolated'); SOURCE=R/'forcing'; PROJECT=R/'selected-project'; EXE=BACK/'data/baseline-diagnostic-source-build-v1/compile-v4/swatplus-research'; CONTRACT=P/'frozen_plant_contract_v2.json'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def prep():
 assert sha(EXE)=='56963a6475aa9014a56a6825749d7fc513fce2dd40dcbb0c0b6a5976364a3c9d'
 R.mkdir(parents=True,exist_ok=True)
 if not SOURCE.exists():
  SOURCE.mkdir()
  with tarfile.open(P/'forcing_inputs.tar.gz') as t:t.extractall(SOURCE,filter='data')
 for name,h in json.loads((P/'forcing_inputs_sha256.json').read_text()).items(): assert sha(SOURCE/name)==h,name
 if not PROJECT.exists(): parameter_project(SOURCE,PROJECT,{'esco':.01,'shallow_flo_min_m':10.,'tile_t_fc_h':6.})
 pm=json.loads((R/'parameter-manifest.json').read_text()); hs={**pm['unchanged_input_sha256'],**{k:v['after'] for k,v in pm['changed_inputs'].items()}}
 for name,h in hs.items(): assert sha(PROJECT/name)==h,name

def cfg(year,identifier):
 return SwatPlusRunConfig(PROJECT,EXE,R/'workspaces',date(year,1,1),date(year,12,31),year-2000,'DAILY','USGS-05451210',identifier,run_type='SWAT_MULTISCALE_COUPLED',outlet_unit='153')
def derive():
 if CONTRACT.exists():
  print('REUSE frozen plant contract',flush=True);return
 print('DERIVE 2010',flush=True)
 c=run_coupled_swat_with_executed_calendar(SwatPlusAdapter(),cfg(2010,'sf-v2-derive-2010'),plant_count=1000,seed=42,parameter_period=(date(2010,1,1),date(2010,12,31)))
 write(CONTRACT,{'derivation_year':2010,'source':'v2-cal-02','summary':c.parameter_summary.model_dump(mode='json'),'input_plants_sha256':sha(PROJECT/'plants.plt'),'source_executable_sha256':sha(EXE),'protocol_sha256':sha(P/'PROTOCOLO.md'),'convergence':c.iterations})
 print('FROZEN',sha(CONTRACT),flush=True)

def flatten(day):
 if not day['crop']['active']:return {'active':False,'lai':0.,'root':0.,'biomass':0.,'transpiration':0.,'stress':None}
 f=day['field']; return {'active':True,'lai':f['mean_LAI'],'root':f['root_depth_mean_m'],'biomass':f['biomass_g_plant'],'transpiration':f['actual_ET_mm_day'],'stress':f.get('water_stress',f.get('mean_stress'))}

def annual(year):
 out=P/'annual'/f'{year}.json'
 if out.exists(): print('REUSE',year,flush=True);return
 if not CONTRACT.exists(): raise RuntimeError('2010 contract must be frozen first')
 print('ANNUAL',year,flush=True)
 base=R/'workspaces'/f'sf-v2-{year}-event-calendar'
 existing=sorted((R/'workspaces').glob(f'sf-v2-{year}-coupled-*'))
 if base.exists() and existing:
  def parse(folder):
   status=json.loads((folder/'swat_run_status.json').read_text());assert status['status']=='COMPLETED'
   for name,h in status['output_checksums'].items(): assert sha(folder/name)==h
   parsed=SwatOutputParser(output_frequency='DAILY',outlet_unit='153').parse(folder,start_date=date(year,1,1),end_date=date(year,12,31))
   return SimpleNamespace(records=parsed.records,hru_results=parsed.hru_results,management_events=parsed.management_events,provenance={'input_checksums_after_mutator':SwatPlusAdapter._input_checksums(folder),'input_checksums_before_mutator':SwatPlusAdapter._input_checksums(base)})
  a,b=parse(base),parse(existing[-1]);previous=parse(existing[-2]) if len(existing)>1 else a
  with tempfile.TemporaryDirectory(prefix='swat-v2-mapper-') as td:
   check=Path(td)/'input';copy_inputs(base,check)
   SwatPlantParameterMapper('corn').apply(check,CouplingPlantParameterSummary.model_validate(json.loads(CONTRACT.read_text())['summary']))
   assert sha(check/'plants.plt')==sha(existing[-1]/'plants.plt')
  weights=SwatExecutedCropCalendar.hru_spatial_weights(PROJECT)
  prev_cal=_calendar_from_result(previous,target_crop='corn',config=cfg(year,'recovery'),hru_weights=weights)
  final_cal=_calendar_from_result(b,target_crop='corn',config=cfg(year,'recovery'),hru_weights=weights)
  from app.services.swat_coupled_runner import _signature
  assert _signature(prev_cal)==_signature(final_cal)
  old={(r['period'],r['hru_unit']):r['soil_water_average_mm'] for r in previous.hru_results};new={(r['period'],r['hru_unit']):r['soil_water_average_mm'] for r in b.hru_results}
  assert old.keys()==new.keys(); delta=max(abs(float(old[k])-float(new[k])) for k in old if old[k] is not None and new[k] is not None);assert delta<=.1
  bfspm=run_fspm_on_executed_calendar(project=PROJECT,calendar=prev_cal,start_date=date(year,1,1),end_date=date(year,12,31),plant_count=1000,seed=42,hru_water_results=previous.hru_results)
  c=SimpleNamespace(baseline_result=a,result=b,fspm=bfspm,iterations=[{'iteration':len(existing),'per_hru_calendar_match':True,'max_hru_daily_average_soil_water_delta_mm':delta}])
  print('RECOVER validated SWAT outputs',year,flush=True)
 else:
  c=run_coupled_swat_with_executed_calendar(SwatPlusAdapter(),cfg(year,f'sf-v2-{year}'),plant_count=1000,seed=42,frozen_parameter_summary=CouplingPlantParameterSummary.model_validate(json.loads(CONTRACT.read_text())['summary']))
  a,b=c.baseline_result,c.result
 expected=(date(year,12,31)-date(year,1,1)).days+1
 assert len(a.records)==len(b.records)==expected
 ah=a.provenance['input_checksums_after_mutator'];bh=b.provenance['input_checksums_after_mutator']
 assert [n for n in sorted(set(ah)|set(bh)) if ah.get(n)!=bh.get(n)]==['plants.plt']
 assert ah['plants.plt']==a.provenance['input_checksums_before_mutator']['plants.plt']
 source_plants_hash=sha(PROJECT/'plants.plt')
 assert source_plants_hash==json.loads(CONTRACT.read_text())['input_plants_sha256']
 calendar=_calendar_from_result(a,target_crop='corn',config=cfg(year,'passive'),hru_weights=SwatExecutedCropCalendar.hru_spatial_weights(PROJECT))
 passive=run_fspm_on_executed_calendar(project=PROJECT,calendar=calendar,start_date=date(year,1,1),end_date=date(year,12,31),plant_count=1000,seed=42,hru_water_results=a.hru_results)
 assert sha(PROJECT/'plants.plt')==source_plants_hash
 weather,_=SwatClimateForcingReader(PROJECT).for_hrus(date(year,1,1),date(year,12,31),require_fspm=False)
 w={r['date']:r for r in weather}
 data={}
 for arm,sim,fspm in [('A',a,passive),('B',b,c.fspm)]:
  data[arm]=[{'day':r['period'],'q':r['streamflow_m3s'],'et':r['evapotranspiration_mm'],'pet':r['potential_evapotranspiration_mm'],'perco':r['percolation_mm'],'tile':r['tile_drainage_mm'],'runoff':r['runoff_mm'],'soil':r['soil_water_average_mm'],'fspm':flatten(fspm.fspm_days[r['period']]),'weather':w[r['period']]} for r in sim.records]
 write(out,{'year':year,'plant_contract_sha256':sha(CONTRACT),'A_plants_sha256':ah['plants.plt'],'B_plants_sha256':bh['plants.plt'],'other_inputs_identical':True,'B_convergence':[{'iteration':x['iteration'],'calendar_match':x['per_hru_calendar_match'],'water_delta_mm':x['max_hru_daily_average_soil_water_delta_mm']} for x in c.iterations],'data':data})
 print('DONE',year,flush=True)
 # Runtime workspaces are regenerable and expensive; preserve selected compact daily outputs and hashes.
 shutil.rmtree(R/'workspaces',ignore_errors=True); gc.collect()
if __name__=='__main__':
 try:
  prep();derive()
  for y in ([] if sys.argv[1:]==['--derive-only'] else map(int,sys.argv[1:]) if len(sys.argv)>1 else range(2013,2026)):annual(y)
 except Exception as e:
  with (P/'ejecucion_errores.log').open('a') as f: traceback.print_exc(file=f)
  raise
