// Presentation regression using stored research artifacts; never touches the DB.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const domain = new URL('../../research_domain/', import.meta.url);
const readJSON = async (name) => JSON.parse(await readFile(new URL(name, domain), 'utf8'));
const frozen = await readJSON('south_fork_test_delivery_4_v1.json');
const report = await readJSON('final_report_v2.json');
const status = await readJSON('current_contract_status.json');
const summary = { ...report,
  runs: Object.fromEntries(['baseline', 'coupled'].map((key) => [key, {
    run_id: report[key].run_id, evidence_type: report[key].provenance.evidence_type, totals: report[key].totals }])),
  validation: Object.fromEntries(['daily', 'monthly_primary'].map((period) => {
    const value = report.validation[period];
    const metrics = (key) => Object.fromEntries(['rmse', 'nse', 'kge', 'pbias', 'r2', 'mae']
      .map((name) => [name, value[key][name]?.value ?? null]));
    return [period, { ...value.alignment, hypothesis_status: value.hypothesis_status,
      improvement_percent: value.improvement_percent?.value ?? null,
      baseline: metrics('baseline'), coupled: metrics('twin') }];
  })),
  scenarios: Object.entries(report.scenarios).map(([name, value]) => ({ name, ...value })),
};
const csv = (await readFile(new URL('test_v1/monthly-predictions.csv', domain), 'utf8')).trim().split('\n');
const columns = csv.shift().split(',');
const predictions = csv.map((line) => {
  const row = Object.fromEntries(line.split(',').map((value, index) => [columns[index], value]));
  return { month: row.month, series: row.series, variant: row.variant, eligible: row.eligible === 'True',
    observed: row.observed_streamflow_m3s ? Number(row.observed_streamflow_m3s) : null,
    predicted: row.predicted_streamflow_m3s ? Number(row.predicted_streamflow_m3s) : null };
});
const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'],
  ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
try {
  const context = await browser.newContext();
  await context.addInitScript(() => localStorage.setItem('digitaltwin_token', 'presentation-fixture'));
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body = [];
    if (path.endsWith('/auth/me')) body = { id: 'presentation-owner', email: 'fixture@example.org',
      full_name: 'Presentation fixture', roles: [{ id: 'r', name: 'INVESTIGADOR_HIDROLOGO' }] };
    else if (path.endsWith('/research/south-fork')) body = { ...frozen,
      sensitivity: frozen.exclude_estimated_sensitivity, predictions, paper_available: true,
      publications: frozen.publications.map((pair) => ({ year: pair.year, A: null, B: null })) };
    else if (path.endsWith('/reports/final-scientific')) body = { ...status,
      current_contract: { ...status.current_contract, current_execution_status: 'EXECUTED' }, current_result: summary };
    else if (path.endsWith('/simulations/capabilities')) body = {};
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
  });
  const base = process.env.VISUAL_BASE_URL ?? 'http://localhost:3000';
  const noHypothesis = async () => assert.doesNotMatch(
    await page.locator('main').first().innerText(), /\bH[01]\b|hipótesis|hypothesis|H1_SUPPORTED|H1_NOT_SUPPORTED/i);
  for (const path of ['/', '/reports']) {
    await page.goto(`${base}${path}`, { waitUntil: 'networkidle', timeout: 90000 });
    await page.getByRole('heading', { name: 'Comparación de caudal mensual', exact: true }).waitFor().catch(async (error) => {
      console.error(path, errors, (await page.locator('body').innerText()).slice(0, 2500));
      throw error;
    });
    assert.ok(await page.locator('table').count() > 0, `${path} must preserve its tables`);
    assert.ok(await page.locator('.recharts-wrapper').count() > 0, `${path} must preserve its charts`);
    await noHypothesis();
  }
  await page.goto(`${base}/simulations`, { waitUntil: 'networkidle', timeout: 90000 });
  await page.getByRole('heading', { name: 'Consola de simulaciones ecohidrológicas', exact: true }).waitFor();
  await noHypothesis();
  for (const label of ['Validación del modelo', 'Escenarios climáticos', 'Batería estadística']) {
    await page.getByRole('button', { name: label, exact: true }).click();
    await noHypothesis();
  }
  await page.getByRole('button', { name: 'Corridas de simulación', exact: true }).click();
  await page.getByRole('button', { name: 'Configurar corrida', exact: true }).waitFor();
  assert.deepEqual(errors, []);
  console.log('Research presentation passed: tables, charts, all tabs and run controls preserved; H0/H1 omitted.');
} finally {
  await browser.close();
}
