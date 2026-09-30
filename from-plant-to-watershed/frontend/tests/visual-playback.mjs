// Optional browser test: set PLAYWRIGHT_MODULE if Playwright is installed outside this package.
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE ?? 'playwright');
import { readFile, mkdir } from 'node:fs/promises';
import { join } from 'node:path';
const fixture=JSON.parse(await readFile(new URL('./fixtures/twin-visual-fixtures.json',import.meta.url),'utf8'));
const withTestBasin = page => ({
  ...page,
  records:page.records.map(record => ({...record,watershed_code:'TEST_FIXTURE_BASIN'})),
});
const coupledDaily=withTestBasin(fixture.pages.coupled_daily);
const coupledMonthly=withTestBasin(fixture.pages.coupled_monthly);
const historicalPage=fixture.pages.historical;
const runs=[
  {id:'fixture-coupled',name:'Fixture acoplado (solo pruebas)',user_id:'u1',status:'COMPLETED',station_id:null,hydrology_backend:'SIMPLIFIED',duration_days:3,effective_config:{watershed_id:'TEST_BASIN_ONLY'}},
  {id:'fixture-historical',name:'Fixture histórico (solo pruebas)',user_id:'u1',status:'COMPLETED',station_id:null,hydrology_backend:'SWAT_PLUS',duration_days:3,effective_config:{watershed_id:'TEST_BASIN_ONLY'}},
];

const output = process.env.VISUAL_OUTPUT_DIR ?? '/tmp/gemelo-visual';
const captureScreenshots = process.env.VISUAL_SCREENSHOTS === '1';
if (captureScreenshots) await mkdir(output,{recursive:true});
const launchOptions = {headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-webgl']};
if(process.env.CHROMIUM_PATH) launchOptions.executablePath=process.env.CHROMIUM_PATH;
const browser=await chromium.launch(launchOptions);
const errors=[];
async function openViewer(firstRun, requestedId) {
  const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  await context.addInitScript(() => localStorage.setItem('digitaltwin_token','fixture-token'));
  const page=await context.newPage();
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',message=>{if(message.type()==='error') errors.push(message.text());});
  await page.route('**/*',async route=>{
    const url=new URL(route.request().url());
    if(!url.pathname.includes('/api/v1/')) return route.continue();
    const p=url.pathname;let body={};
    if(p.endsWith('/auth/me')) body={id:'u1',email:'fixture@example.org',full_name:'Fixture',roles:[{id:'r',name:'SUPERADMIN'}]};
    else if(p.endsWith('/simulations')) body=firstRun==='historical'?[runs[1],runs[0]]:runs;
    else if(p.endsWith('/simulations/fixture-coupled/availability')) body={simulation_id:'fixture-coupled',simulation_name:runs[0].name,simulation_status:'COMPLETED',run_type:'SWAT_MULTISCALE_COUPLED',origin:'EXECUTED',provenance_class:'COUPLED_EXECUTED',stored_hydrology_available:true,stored_fspm_summary_available:true,stored_fspm_trajectory_available:true,stored_fspm_samples_available:true,fspm_results_available:true,available_resolutions:['MONTHLY','DAILY'],codes:[],limitations:[],resolutions:[{resolution:'MONTHLY',artifact_status:'AVAILABLE',record_count:1,first_record:'2020-05-01',last_record:'2020-05-01',first_active_crop:null,first_representable_field:null,first_plant_samples:null,crop_intervals:[],hydrology_available:true,fspm_trajectory_available:false,plant_samples_available:false,hru_ids:[],selected_date:null,codes:[]},{resolution:'DAILY',artifact_status:'AVAILABLE',record_count:3,first_record:'2020-05-10',last_record:'2020-11-10',first_active_crop:'2020-05-10',first_representable_field:'2020-05-10',first_plant_samples:'2020-05-10',crop_intervals:[],hydrology_available:true,fspm_trajectory_available:true,plant_samples_available:true,hru_ids:[],selected_date:null,codes:[]}]};
    else if(p.endsWith('/simulations/fixture-coupled/playback')) body=url.searchParams.get('resolution')==='DAILY'?coupledDaily:coupledMonthly;
    else if(p.endsWith('/simulations/fixture-historical/availability')) body={simulation_id:'fixture-historical',simulation_name:runs[1].name,simulation_status:'COMPLETED',run_type:'SWAT_MULTISCALE_COUPLED',origin:'HISTORICAL_IMPORT',provenance_class:'HISTORICAL_IMPORT',stored_hydrology_available:true,stored_fspm_summary_available:false,stored_fspm_trajectory_available:false,stored_fspm_samples_available:false,fspm_results_available:false,available_resolutions:[],codes:['HISTORICAL_REFERENCE','NO_PLAYBACK_ARTIFACT'],limitations:['Fixture sintético sin playback'],resolutions:[]};
    else if(p.endsWith('/simulations/fixture-historical/playback')) body=historicalPage;
    else if(p.endsWith('/simulations/fixture-historical/swat-results')) body={records:[{period:'2020-02-01',streamflow_m3s:7,runoff_mm:0.5,evapotranspiration_mm:2.5,soil_water_mm:160}]};
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
  });
  const simQuery=requestedId ? `?simId=${encodeURIComponent(requestedId)}` : '';
  await page.goto(`${process.env.VISUAL_BASE_URL ?? 'http://localhost:3000'}/twin-3d${simQuery}`,{waitUntil:'domcontentloaded'});
  return {context,page};
}
async function shot(page,name){
  if (captureScreenshots) await page.screenshot({path:join(output,name+'.png'),timeout:30000,animations:'disabled',caret:'hide'});
}
try {
  // Reverse the list order and assert that simId still selects the requested run.
  const scientific=await openViewer('historical','fixture-coupled');
  const p=scientific.page;
  await p.getByText('2020-05-10',{exact:false}).first().waitFor({timeout:30000});
  if (await p.getByLabel('Simulación').inputValue() !== 'fixture-coupled') throw Error('simId did not select the requested run');
  if (await p.getByLabel('Detalle temporal').inputValue() !== 'DAILY') throw Error('Daily FSPM playback was not selected automatically');
  await p.getByText('Geometría espacial no disponible para esta corrida.').waitFor({timeout:30000});
  await shot(p,'scientific-macro');
  await p.getByRole('button',{name:'Campo',exact:true}).first().click({timeout:120000});
  await p.getByText('Campo FSPM · 2020-05-10').waitFor();
  await shot(p,'scientific-meso');
  await p.getByRole('button',{name:'Planta',exact:true}).first().click({timeout:120000});
  await p.getByText('Muestra FSPM test-plant-1').waitFor();
  await shot(p,'scientific-micro-early');
  await p.getByRole('button',{name:'Avanzar'}).dispatchEvent('click');
  await p.getByText('2020-08-10',{exact:false}).first().waitFor();
  await shot(p,'scientific-micro-mature');
  await p.getByRole('button',{name:'Avanzar'}).dispatchEvent('click');
  await p.getByText('2020-11-10',{exact:false}).first().waitFor();
  await p.getByText('Fuera de la temporada de cultivo FSPM: no hay plantas científicas activas en esta fecha.').waitFor();
  await shot(p,'scientific-fallow');
  await scientific.context.close();

  const historical=await openViewer('historical');
  const h=historical.page;
  await h.getByText('Exploración 3D histórica · representación ilustrativa').waitFor({timeout:30000});
  await h.getByText('Cuenca contextual').waitFor({timeout:30000});
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
  console.log(`Visual fixture OK: simId/resolución, tres escalas, fechas de trayectoria y fallback histórico${captureScreenshots ? `; capturas en ${output}` : ''}`);
  await historical.context.close();
} finally {await browser.close();}
