// Browser regression for report availability, downloads and API failure states.
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'],
  ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
const base = process.env.VISUAL_BASE_URL ?? 'http://localhost:3000';
const run = { id: 'swat-report', user_id: 'owner', watershed_id: 'basin', scenario_id: 'scenario',
  name: 'South Fork 2019', status: 'COMPLETED', hydrology_backend: 'SWAT_PLUS', duration_days: 365,
  climate_source: 'SWAT_PROJECT', start_date: '2019-01-01', end_date: '2019-12-31',
  provenance: { evidence_type: 'REAL_SWAT_PLUS_COUPLED' },
  summary_metrics: { total_precip_mm: 0, total_runoff_mm: 12.5 } };
const context = await browser.newContext();
await context.addInitScript(() => localStorage.setItem('digitaltwin_token', 'reports-fixture'));
const page = await context.newPage();
const errors = [];
let failDownload = false;
let failCatalog = false;
let history = [];
page.on('pageerror', error => errors.push(error.message));
await page.route('**/api/v1/**', async route => {
  const path = new URL(route.request().url()).pathname;
  let body = {}, status = 200;
  if (path.endsWith('/auth/me')) body = { id: 'owner', full_name: 'Reports fixture', roles: [{ name: 'INVESTIGADOR_HIDROLOGO' }] };
  else if (path.endsWith('/simulations')) {
    body = failCatalog ? { detail: 'Catálogo no disponible' } : [{ ...run, id: 'pending', name: 'Pendiente', status: 'PENDING' }, run];
    status = failCatalog ? 503 : 200;
  } else if (path.endsWith('/reports/history')) body = history;
  else if (path.includes('/reports/download/')) {
    if (failDownload) return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'No se pudo generar el reporte' }) });
    const format = path.split('/').at(-1);
    history = [{ id: `history-${format}`, filename: `reporte.${format}`, format, simulation_id: run.id,
      simulation_name: run.name, file_size_bytes: 2048, created_at: '2026-10-20 12:00' }];
    return route.fulfill({ status: 200, headers: { 'Content-Type': 'application/octet-stream',
      'Content-Disposition': `attachment; filename="reporte.${format}"`, 'Access-Control-Expose-Headers': 'Content-Disposition' }, body: `report-${format}` });
  } else if (path.endsWith('/reports/final-scientific') || path.endsWith('/research/south-fork') || path.endsWith('/research/south-fork/exports')) {
    status = 503; body = { detail: 'Archivo histórico no disponible' };
  }
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
});
try {
  await page.goto(`${base}/reports`, { waitUntil: 'networkidle', timeout: 90000 });
  const select = page.getByLabel('Corrida', { exact: true });
  await page.waitForFunction(() => document.querySelector('#report-simulation')?.value === 'swat-report');
  assert.equal(await select.inputValue(), run.id, 'Default to a completed run');
  for (const format of ['PDF', 'Word', 'Excel']) {
    const button = page.getByRole('button', { name: new RegExp(`^${format} `) });
    assert.equal(await button.isEnabled(), true, 'SWAT+ must expose all formats');
    const download = page.waitForEvent('download');
    await button.click();
    const file = await download;
    assert.equal(file.suggestedFilename(), `reporte.${{ PDF: 'pdf', Word: 'docx', Excel: 'xlsx' }[format]}`);
    await page.getByRole('status').filter({ hasText: 'se descargó' }).waitFor();
  }
  await page.getByRole('button', { name: 'Volver a descargar reporte.xlsx' }).waitFor();
  const repeatDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Volver a descargar reporte.xlsx' }).click();
  await repeatDownload;
  await select.selectOption('pending');
  assert.equal(await page.getByRole('button', { name: /^PDF / }).isDisabled(), true);
  await select.selectOption(run.id);
  failDownload = true;
  await page.getByRole('button', { name: /^PDF / }).click();
  await page.getByRole('alert').filter({ hasText: 'No se pudo generar el reporte' }).waitFor();
  assert.equal(await page.getByRole('button', { name: /^PDF / }).isEnabled(), true);
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  assert.ok((await page.locator('main').boundingBox()).width >= 350, 'Mobile reports must retain readable width');
  await page.locator('details > summary').filter({ hasText: 'Módulos' }).click();
  await page.getByRole('link', { name: 'Reportes y Evidencia' }).filter({ visible: true }).click();
  await page.locator('main').evaluate(element => element.scrollTop = 0);
  if (process.env.VISUAL_SCREENSHOTS) {
    const dir = process.env.VISUAL_OUTPUT_DIR ?? '/tmp/reports-visual';
    await mkdir(dir, { recursive: true });
    await page.screenshot({ path: `${dir}/reports-mobile.png`, fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.locator('main').evaluate(element => element.scrollTop = 0);
    await page.screenshot({ path: `${dir}/reports-desktop.png`, fullPage: true });
  }
  failCatalog = true;
  await page.getByRole('button', { name: 'Actualizar datos' }).click();
  await page.getByRole('alert').filter({ hasText: 'Catálogo no disponible' }).waitFor();
  assert.equal(await page.getByRole('button', { name: /^PDF / }).isDisabled(), true);
  assert.deepEqual(errors, []);
  console.log('Reports browser regression passed: SWAT+ downloads, history, pending, errors and mobile.');
} finally {
  await context.close();
  await browser.close();
}
