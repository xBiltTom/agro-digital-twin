// Optional browser test: set PLAYWRIGHT_MODULE if Playwright is installed outside this package.
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE ?? 'playwright');
import { mkdir } from 'node:fs/promises';
import { join } from 'node:path';
const available = (value, unit, evidence='SIMPLIFIED_FSPM') => ({ value, unit, evidence, source:'fixture-local', availability:'AVAILABLE', limitation:null });
const absent = (unit) => ({ value:null, unit, evidence:'NOT_AVAILABLE', source:'fixture-local', availability:'NOT_AVAILABLE', limitation:null });
function record(date, height, rain, active=true) {
  return { schema_version:'twin-playback-v1', simulation_id:'scientific', date, resolution:'DAILY', run_type:'SWAT_MULTISCALE_COUPLED', watershed_id:'south-fork', watershed_code:'South Fork Iowa River', outlet_unit:'m3/s', spatial_support:'WATERSHED_OUTLET_AND_BASIN',
    weather:{precipitation_mm:available(rain,'mm/day','DERIVED'),temperature_c:available(23,'degC','DERIVED')},
    crop:{active,crop:active?'maize':null,season_id:active?'season-2020':null,phenological_stage:active?height>1?'REPRODUCTIVE':'EMERGENCE':null,window_status:'APPROXIMATE_PLANTING_WINDOW',source:'fixture-local',limitation:null},
    field:active?{height_m:available(height,'m'),lai:available(height>1?3.5:0.5,'m2_leaf/m2_ground'),root_depth_m:available(height>1?1.1:0.15,'m'),canopy_cover_fraction:available(height>1?0.8:0.1,'fraction'),water_stress:available(0.3,'fraction'),actual_transpiration_mm_day:available(1.2,'mm/day'),soil_moisture_vol_percent:available(24,'volumetric percent','ASSUMED')}: {},
    plant_samples:active?[{plant_id:'maize-00001',x_m:0,y_m:0,variables:{height_m:available(height,'m'),lai:available(height>1?3.5:0.5,'m2_leaf/m2_ground'),root_depth_m:available(height>1?1.1:0.15,'m'),water_stress:available(0.3,'fraction'),phenological_stage:available(height>1?'REPRODUCTIVE':'EMERGENCE','category'),actual_transpiration_mm_day:available(1.2,'mm/day')}}]:[],
    hydrology:{streamflow_m3s:available(8,'m3/s','MODELLED_SWAT_PLUS'),runoff_mm:available(0.4,'mm/day','MODELLED_SWAT_PLUS'),evapotranspiration_mm:available(3,'mm/day','MODELLED_SWAT_PLUS'),percolation_mm:available(1,'mm/day','MODELLED_SWAT_PLUS'),soil_water_mm:available(170,'mm','MODELLED_SWAT_PLUS'),observed_streamflow_m3s:absent('m3/s')},
    hru_results:[],availability:{},limitations:[] };
}
const records=[record('2020-05-01',0.25,0),record('2020-08-01',2.25,6),record('2020-11-01',0,0,false)];
const runs=[{id:'scientific',name:'Fixture científico',user_id:'u1',status:'COMPLETED',station_id:'05451210',hydrology_backend:'SWAT_PLUS',duration_days:3,effective_config:{watershed_id:'south-fork'}},{id:'historical',name:'Fixture histórico',user_id:'u1',status:'COMPLETED',station_id:'05451210',hydrology_backend:'SWAT_PLUS',duration_days:3,effective_config:{watershed_id:'south-fork'}}];

const output = process.env.VISUAL_OUTPUT_DIR ?? '/tmp/gemelo-visual';
await mkdir(output,{recursive:true});
const launchOptions = {headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-webgl']};
if(process.env.CHROMIUM_PATH) launchOptions.executablePath=process.env.CHROMIUM_PATH;
const browser=await chromium.launch(launchOptions);
const errors=[];
async function openViewer(firstRun) {
  const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  await context.addInitScript(() => localStorage.setItem('digitaltwin_token','fixture-token'));
  const page=await context.newPage();
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('http://localhost:8000/api/v1/**',async route=>{
    const url=new URL(route.request().url());const p=url.pathname;let body={};
    if(p.endsWith('/auth/me')) body={id:'u1',email:'fixture@example.org',full_name:'Fixture',roles:[{id:'r',name:'SUPERADMIN'}]};
    else if(p.endsWith('/simulations')) body=firstRun==='historical'?[runs[1],runs[0]]:runs;
    else if(p.endsWith('/simulations/scientific/playback')) body={schema_version:'twin-playback-v1',simulation_id:'scientific',simulation_status:'COMPLETED',artifact_status:'AVAILABLE',resolution:'DAILY',available_resolutions:['DAILY'],total:3,offset:0,limit:100,records,variables:{},provenance:{},limitations:[]};
    else if(p.endsWith('/simulations/historical/playback')) body={schema_version:'twin-playback-v1',simulation_id:'historical',simulation_status:'COMPLETED',artifact_status:'NOT_AVAILABLE',resolution:null,available_resolutions:[],total:0,offset:0,limit:100,records:[],variables:{},provenance:{},limitations:['Sin artefacto']};
    else if(p.endsWith('/simulations/historical/swat-results')) body={records:[{period:'2020-02-01',streamflow_m3s:7,runoff_mm:0.5,evapotranspiration_mm:2.5,soil_water_mm:160}]};
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
  });
  await page.goto(`${process.env.VISUAL_BASE_URL ?? 'http://127.0.0.1:3001'}/twin-3d`,{waitUntil:'domcontentloaded'});
  return {context,page};
}
async function shot(page,name){ await page.screenshot({path:join(output,name+'.png'),timeout:120000}); }
try {
  const scientific=await openViewer('scientific');
  const p=scientific.page;
  await p.getByText('2020-05-01 · DAILY').waitFor({timeout:30000});
  await p.getByText('Contorno contextual · South Fork Iowa (no reconstrucción GIS validada)').waitFor({timeout:30000});
  await shot(p,'scientific-macro');
  await p.getByRole('button',{name:'Campo',exact:true}).first().click({timeout:120000});
  await p.getByText('Campo FSPM · 2020-05-01').waitFor();
  await shot(p,'scientific-meso');
  await p.getByRole('button',{name:'Planta',exact:true}).first().click({timeout:120000});
  await p.getByText('Muestra FSPM maize-00001').waitFor();
  await shot(p,'scientific-micro-early');
  await p.getByRole('button',{name:'Avanzar'}).click();
  await p.getByText('2020-08-01 · DAILY').waitFor();
  await shot(p,'scientific-micro-mature');
  await p.getByRole('button',{name:'Avanzar'}).click();
  await p.getByText('2020-11-01 · DAILY').waitFor();
  await p.getByText('Esta corrida/fecha no contiene muestra FSPM activa.').waitFor();
  await shot(p,'scientific-fallow');
  await scientific.context.close();

  const historical=await openViewer('historical');
  const h=historical.page;
  await h.getByText('Exploración 3D histórica · representación ilustrativa').waitFor({timeout:30000});
  await h.getByText('Contorno contextual · South Fork Iowa (no reconstrucción GIS validada)').waitFor({timeout:30000});
  await shot(h,'historical-macro');
  await h.getByRole('button',{name:'Campo',exact:true}).last().dispatchEvent('click');
  await h.getByText('Parcela de referencia · ilustrativa').waitFor({timeout:30000});
  await shot(h,'historical-meso');
  await h.getByRole('button',{name:'Planta',exact:true}).last().dispatchEvent('click');
  await h.getByText('Maíz de referencia · ilustrativo').waitFor({timeout:30000});
  await shot(h,'historical-micro');
  await h.locator('canvas').first().hover();
  await h.mouse.down(); await h.mouse.move(700,520,{steps:6}); await h.mouse.up(); await h.mouse.wheel(0,250);
  if(errors.length) throw Error('Browser errors: '+errors.join('; '));
  console.log('Visual fixture OK: 8 capturas, tres escalas científicas e históricas, fechas y temporada; '+output);
  await historical.context.close();
} finally {await browser.close();}
