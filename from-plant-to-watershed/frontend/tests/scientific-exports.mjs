// Browser → real API → frozen artifacts → previews and downloads.
// Run against a disposable backend database with the standard demo user seeded.
import assert from "node:assert/strict";
import { mkdir, readFile } from "node:fs/promises";
import { chromium } from "playwright";

const base = process.env.VISUAL_BASE_URL ?? "http://localhost:3000";
const api = process.env.SCIENTIFIC_API_URL ?? "http://localhost:8000/api/v1";
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"],
  ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
const context = await browser.newContext();
const page = await context.newPage();
const errors = [];
page.on("pageerror", error => errors.push(error.message));

async function preview(panel, title) {
  const img = panel.getByRole("img", { name: `Vista previa de ${title}` });
  await img.waitFor();
  await img.evaluate(image => image.decode());
  assert.ok(await img.evaluate(image => image.naturalWidth > 1000));
}

try {
  const login = await context.request.post(`${api}/auth/login`, {
    data: { email: "investigador@digitaltwin.org", password: "Investiga123!" },
  });
  assert.equal(login.status(), 200);
  const { access_token: token } = await login.json();
  await context.addInitScript(value => localStorage.setItem("digitaltwin_token", value), token);
  const catalog = await context.request.get(`${api}/research/south-fork/exports`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const { entries } = await catalog.json();
  assert.equal(entries.length, 8);

  await page.goto(`${base}/reports`, { waitUntil: "networkidle", timeout: 90000 });
  const panel = page.locator("details").filter({ has: page.locator("summary", { hasText: /^Figuras y tablas científicas$/ }) });
  const selector = panel.getByLabel("Figura o tabla", { exact: true });
  for (const entry of entries) {
    await selector.selectOption(entry.id);
    await preview(panel, entry.title);
  }
  await selector.selectOption("performance");
  await panel.getByLabel("Observaciones", { exact: true }).selectOption("EXCLUDE_ESTIMATED");
  await preview(panel, entries.find(item => item.id === "performance").title);
  for (const format of ["png", "svg", "pdf", "csv"]) {
    const pending = page.waitForEvent("download");
    await panel.getByRole("button", { name: `Descargar ${format.toUpperCase()}`, exact: true }).click();
    const download = await pending;
    assert.equal(download.suggestedFilename(), `sf-test-v1_performance_exclude_estimated.${format}`);
    const data = await readFile(await download.path());
    if (format === "png") assert.deepEqual([...data.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
    if (format === "svg") assert.match(data.toString(), /<svg/);
    if (format === "pdf") assert.ok(data.toString().startsWith("%PDF-"));
    if (format === "csv") {
      assert.match(data.toString(), /Métrica,A,B,C,D/);
      assert.match(data.toString(), /RMSE \(m³\/s\),4\.42/);
    }
  }

  // A rejected download gives feedback and permits retry.
  await page.route("**/exports/performance/pdf?*", route => route.fulfill({ status: 503,
    contentType: "application/json", headers: { "Access-Control-Allow-Origin": new URL(base).origin },
    body: JSON.stringify({ detail: "Exportación temporalmente no disponible" }) }));
  await panel.getByRole("button", { name: "Descargar PDF", exact: true }).click();
  await panel.getByRole("alert").filter({ hasText: "Exportación temporalmente no disponible" }).waitFor();
  assert.equal(await panel.getByRole("button", { name: "Descargar PDF", exact: true }).isEnabled(), true);
  await page.unroute("**/exports/performance/pdf?*");
  const retry = page.waitForEvent("download");
  await panel.getByRole("button", { name: "Descargar PDF", exact: true }).click();
  await retry;
  await panel.getByRole("status").filter({ hasText: "se descargó" }).waitFor();

  // Closing revokes the preview URL; reopening must generate a usable preview.
  await panel.locator("summary").click();
  await panel.locator("summary").click();
  await preview(panel, entries.find(item => item.id === "performance").title);
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  const output = process.env.VISUAL_OUTPUT_DIR ?? "/tmp/scientific-exports-browser";
  await mkdir(output, { recursive: true });
  await panel.screenshot({ path: `${output}/exports-mobile.png` });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await panel.screenshot({ path: `${output}/exports-desktop.png` });

  await page.goto(`${base}/datasets`, { waitUntil: "networkidle" });
  const partitions = page.locator("details").filter({ hasText: "Figuras y tablas del protocolo temporal" });
  await partitions.locator("summary").click();
  await partitions.getByLabel("Figura o tabla", { exact: true }).waitFor();
  assert.equal(await partitions.getByLabel("Figura o tabla", { exact: true }).locator("option").count(), 2);
  await preview(partitions, entries.find(item => item.id === "temporal-partition").title);

  await page.goto(`${base}/simulations`, { waitUntil: "networkidle" });
  const simulations = page.locator("details").filter({ has: page.locator("summary", { hasText: /^Figuras y tablas científicas$/ }) });
  await simulations.locator("summary").click();
  await simulations.getByLabel("Figura o tabla", { exact: true }).waitFor();
  assert.equal(await simulations.getByLabel("Figura o tabla", { exact: true }).locator("option").count(), 6);
  await simulations.getByLabel("Figura o tabla", { exact: true }).selectOption("plant-mapping");
  await preview(simulations, entries.find(item => item.id === "plant-mapping").title);
  assert.deepEqual(errors, []);
  console.log("Scientific exports browser regression passed: 8 previews, 4 real downloads, sensitivity, retry, reopen, mobile and module scopes.");
} finally {
  await context.close();
  await browser.close();
}
