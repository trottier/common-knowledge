import { test, expect } from "@playwright/test";
import { resolve, join } from "node:path";
import { pathToFileURL } from "node:url";

test("double-click HTML reads the chosen map offline and supports re-selection", async ({ page }) => {
  test.skip(!process.env.CK_VIEWER_DIR, "Build tools/laptop_fixture.py or a checked viewer bundle first.");
  const folder = resolve(process.env.CK_VIEWER_DIR);
  const http = [], errors = [], policy = [];
  page.on("request", (request) => { if (/^https?:/i.test(request.url())) http.push(request.url()); });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.addInitScript(() => {
    document.addEventListener("securitypolicyviolation", (event) => console.error(`CSP: ${event.blockedURI} ${event.violatedDirective}`));
  });
  page.on("console", (message) => { if (message.text().startsWith("CSP:")) policy.push(message.text()); });
  await page.goto(pathToFileURL(join(folder, "1_OPEN_MAP.html")).href);
  const status = page.locator("#status");
  await page.locator("#file").setInputFiles({ name: "bad.pmtiles", mimeType: "application/octet-stream", buffer: Buffer.from("wrong map") });
  await expect(status).toHaveText("Choose the supplied map file from this folder.");
  const mapFile = join(folder, "2_US_ROADS.pmtiles");
  for (let count = 0; count < 2; count++) {
    await page.locator("#file").setInputFiles(mapFile);
    await expect(status).toContainText("Map ready.", { timeout: 30000 });
    await page.locator("#latitude").fill("0");
    await page.locator("#longitude").fill("0");
    await page.getByRole("button", { name: "Go to coordinates" }).click();
    await expect(page.locator("#position")).toHaveText("0.00000, 0.00000");
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
    await page.locator("#region").selectOption("RI");
    await page.getByRole("button", { name: "U.S. overview" }).click();
    await expect(page.locator("canvas.maplibregl-canvas")).toBeVisible();
  }
  if (process.env.CK_SCREENSHOT) await page.screenshot({ path: process.env.CK_SCREENSHOT });
  expect(http).toEqual([]);
  expect(errors).toEqual([]);
  expect(policy).toEqual([]);
});
