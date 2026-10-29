from pathlib import Path
import sys, tempfile, tarfile, json, hashlib
from datetime import date
repo=Path.cwd(); root=repo/'from-plant-to-watershed'; back=root/'backend';p=root/'research_domain/experiment_v2'
sys.path[:0]=[str(back),str(back/'scripts')]
from run_south_fork_multiyear import parameter_project
from app.services.swat_plus_adapter import SwatPlusAdapter,SwatPlusRunConfig
with tempfile.TemporaryDirectory(prefix='southfork-physical-clean-') as d:
 t=Path(d);source=t/'forcing';source.mkdir()
 with tarfile.open(p/'forcing_inputs.tar.gz') as tf: tf.extractall(source,filter='data')
 manifest=json.loads((p/'forcing_inputs_sha256.json').read_text())
 for name,hashval in manifest.items(): assert hashlib.sha256((source/name).read_bytes()).hexdigest()==hashval
 values={'esco':.01,'shallow_flo_min_m':10.,'tile_t_fc_h':6.}
 parameter_project(source,t/'candidate/project',values)
 cfg=SwatPlusRunConfig(t/'candidate/project',back/'data/baseline-diagnostic-source-build-v1/compile-v4/swatplus-research',t/'workspace',date(2005,1,1),date(2012,12,31),5,'MONTHLY','USGS-05451210','v2-clean-check',outlet_unit='153')
 result=SwatPlusAdapter().run(cfg)
 pred={r['period'][:7]:r['streamflow_m3s'] for r in result.records}
 stored=json.loads((p/'runs/v2-cal-02/result.json').read_text())['predictions']
 assert pred==stored
 print('198 inputs verified; v2-cal-02 96 monthly flows exactly reproduced in clean folder with existing backend environment and executable.')
