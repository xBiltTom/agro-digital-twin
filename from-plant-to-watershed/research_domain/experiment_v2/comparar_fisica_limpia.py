"""Compare physically re-executed annual series with original v2 outputs."""
from pathlib import Path
import argparse,hashlib,json
p=Path(__file__).resolve().parent
arg=argparse.ArgumentParser();arg.add_argument('clean_directory',type=Path);args=arg.parse_args()
clean=args.clean_directory; original=json.loads((p/'frozen_plant_contract_v2.json').read_text());repeat=json.loads((clean/'frozen_plant_contract_v2.json').read_text()); assert original['summary']==repeat['summary']
rows=[]
for year in range(2013,2026):
 a=json.loads((p/'annual'/f'{year}.json').read_text());b=json.loads((clean/'annual'/f'{year}.json').read_text())
 for k in ['data','A_plants_sha256','B_plants_sha256','other_inputs_identical']: assert a[k]==b[k],(year,k)
 rows.append({'year':year,'daily_pairs':len(a['data']['A']),'data_equal':True,'A_plants_sha256':a['A_plants_sha256'],'B_plants_sha256':a['B_plants_sha256'],'original_sha256':hashlib.sha256((p/'annual'/f'{year}.json').read_bytes()).hexdigest(),'repeat_sha256':hashlib.sha256((clean/'annual'/f'{year}.json').read_bytes()).hexdigest()})
print(json.dumps({'plant_summary_equal':True,'daily_values_exact':True,'years':rows},indent=2))
