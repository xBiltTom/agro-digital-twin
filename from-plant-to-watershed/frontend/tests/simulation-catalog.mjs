// Run against a local Next.js server. API fixtures never touch the real DB.
import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const browser = await chromium.launch({
  headless: true,
  args: ['--no-sandbox'],
  ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
});
const base = process.env.VISUAL_BASE_URL ?? 'http://localhost:3000';
const emptyMessage = 'No se encontraron simulaciones que coincidan con la búsqueda.';
const runs = ['A', 'B'].map((arm) => ({
  id: `catalog-${arm}`, user_id: 'catalog-owner', watershed_id: 'basin', scenario_id: 'scenario',
  name: `Catalogue ${arm}`, status: 'PENDING', duration_days: 365, seed: 42,
  hydrology_backend: 'SIMPLIFIED', mode: 'RESEARCH_MULTISCALE', plant_count: 100,
  climate_source: 'SYNTHETIC', management_scenario: 'BASELINE', summary_metrics: {},
  start_date: '2019-01-01', end_date: '2019-12-31', provenance: {},
}));
function gate() {
  let release;
  const promise = new Promise((resolve) => { release = resolve; });
  return { promise, release };
}
async function openPage({ failCatalog = false } = {}) {
  const context = await browser.newContext();
  await context.addInitScript(() => localStorage.setItem('digitaltwin_token', 'catalog-fixture-token'));
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  const catalog = gate(), report = gate(), configuration = gate(), detailA = gate();
  let reportFinished = false;
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url());
    let body = {}, status = 200;
    if (url.pathname.endsWith('/auth/me')) {
      body = { id: 'catalog-owner', email: 'catalog@example.org', full_name: 'Catalogue fixture',
        roles: [{ id: 'r', name: 'INVESTIGADOR_HIDROLOGO' }] };
    } else if (url.pathname.endsWith('/simulations')) {
      assert.equal(url.searchParams.get('view'), 'summary');
      await catalog.promise;
      status = failCatalog ? 503 : 200;
      body = failCatalog ? { detail: 'Catálogo temporalmente no disponible' } : runs;
    } else if (url.pathname.endsWith('/simulations/catalog-A')) {
      await detailA.promise;
      body = runs[0];
    } else if (url.pathname.endsWith('/simulations/catalog-B')) {
      body = runs[1];
    } else if (url.pathname.endsWith('/reports/final-scientific')) {
      await report.promise;
      reportFinished = true;
      status = 503; body = { detail: 'Informe temporalmente no disponible' };
    } else if (url.pathname.endsWith('/simulations/scenarios/all')) {
      await configuration.promise;
      body = [];
    } else if (url.pathname.endsWith('/simulations/watersheds/all') || url.pathname.endsWith('/datasets')) {
      body = [];
    } else if (url.pathname.endsWith('/research/south-fork')) {
      status = 503; body = { detail: 'Research fixture unavailable' };
    }
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.goto(`${base}/simulations`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  return { context, page, pageErrors, catalog, report, configuration, detailA,
    reportFinished: () => reportFinished };
}
try {
  const fixture = await openPage();
  const { page } = fixture;
  await page.getByText('Cargando simulaciones…', { exact: true }).waitFor({ timeout: 60000 });
  assert.equal(await page.getByText(emptyMessage, { exact: true }).count(), 0);
  fixture.catalog.release();
  const cardB = page.getByRole('button', { name: /Catalogue B/ });
  await cardB.waitFor({ timeout: 15000 });
  assert.equal(fixture.reportFinished(), false, 'Catalogue must appear while the report is still pending');

  await cardB.click();
  await page.getByRole('heading', { name: 'Catalogue B', exact: true }).waitFor();
  const oldDetail = page.waitForResponse((response) => response.url().endsWith('/simulations/catalog-A'));
  fixture.detailA.release();
  await oldDetail;
  await page.evaluate(() => new Promise(requestAnimationFrame));
  assert.equal(await page.getByRole('heading', { name: 'Catalogue B', exact: true }).count(), 1,
    'A delayed previous selection must not replace the selected run');

  const reportResponse = page.waitForResponse((response) => response.url().endsWith('/reports/final-scientific'));
  fixture.report.release(); fixture.configuration.release();
  await reportResponse;
  await cardB.waitFor();
  assert.deepEqual(fixture.pageErrors, []);
  await fixture.context.close();

  const unavailable = await openPage({ failCatalog: true });
  unavailable.catalog.release(); unavailable.report.release(); unavailable.configuration.release();
  await unavailable.page.getByRole('alert').getByText('Catálogo temporalmente no disponible', { exact: true }).waitFor();
  assert.equal(await unavailable.page.getByText(emptyMessage, { exact: true }).count(), 0);
  assert.deepEqual(unavailable.pageErrors, []);
  await unavailable.context.close();
  console.log('Catalogue browser regression passed: loading, independent report/configuration, selection race, and API error.');
} finally {
  await browser.close();
}
