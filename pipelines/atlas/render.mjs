import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { promisify } from "node:util";
import { createRequire } from "node:module";
import { PMTiles } from "pmtiles";
import sharp from "sharp";
import { LocalSource, resource } from "./source.mjs";
import { style } from "./style.mjs";
import { loadStyleWithGlyphs } from "./glyphs.mjs";

const require = createRequire(import.meta.url);
const native = require("@maplibre/maplibre-gl-native");
const fontnik = require("fontnik");
const glyphRange = promisify(fontnik.range);
sharp.concurrency(1);

async function checksum(path) {
  const hash = createHash("sha256");
  for await (const block of createReadStream(path)) hash.update(block);
  return hash.digest("hex");
}

if (process.argv.length !== 3 || process.argv[2] === "--help") {
  console.log("Usage: bun run render /artifacts/atlas/STATE/jobs.json");
  process.exit(process.argv[2] === "--help" ? 0 : 1);
}
const jobPath = resolve(process.argv[2]);
const jobs = JSON.parse(await readFile(jobPath, "utf8"));
if (jobs.schema !== 1 || !Array.isArray(jobs.pages) || !jobs.pages.length) {
  throw new Error("Invalid atlas render job");
}
if (!jobs.basemap || !jobs.font) throw new Error("Attach a verified basemap before rendering");
for (const input of [jobs.basemap, jobs.font]) {
  if (await checksum(input.path) !== input.sha256) throw new Error("Atlas input checksum mismatch");
}
const source = new LocalSource(jobs.basemap.path, jobs.basemap.sha256);
const tiles = new PMTiles(source);
const header = await tiles.getHeader();
if (header.tileType !== 1) throw new Error("Atlas requires vector PMTiles");
const font = await readFile(jobs.font.path);
const glyphs = new Map();
const errors = [];
const map = new native.Map({
  ratio: 1,
  request(request, callback) {
    Promise.resolve().then(async () => {
      const parsed = resource(request.url);
      if (parsed.kind === "tile") {
        const tile = await tiles.getZxy(parsed.z, parsed.x, parsed.y);
        return tile ? Buffer.from(tile.data) : null;
      }
      const key = `${parsed.start}-${parsed.end}`;
      if (!glyphs.has(key)) {
        glyphs.set(key, glyphRange({ font, start: parsed.start, end: parsed.end }));
      }
      return await glyphs.get(key);
    }).then(data => data ? callback(null, { data }) : callback()).catch(error => {
      errors.push(error.message);
      callback(error);
    });
  },
});
const outputs = [];
const packages = JSON.parse(await readFile(new URL("./package.json", import.meta.url), "utf8"));
try {
  await loadStyleWithGlyphs(map, fontnik, font, style(header.maxZoom));
  for (const page of jobs.pages) {
    if (!/^[a-zA-Z0-9_-]+$/.test(page.id) || !Number.isInteger(page.width) ||
        !Number.isInteger(page.height) || page.width < 1 || page.width > 1920 ||
        page.height < 1 || page.height > 2400 || !Number.isFinite(page.zoom) ||
        page.zoom < header.minZoom || page.zoom > header.maxZoom ||
        !page.center.every(Number.isFinite)) throw new Error("Unsupported atlas viewport");
    const pixels = await new Promise((accept, reject) => {
      map.render({ width: page.width, height: page.height, center: page.center,
        zoom: page.zoom, bearing: 0, pitch: 0 }, (error, data) => error ? reject(error) : accept(data));
    });
    if (errors.length) throw new Error(`Atlas resources failed: ${errors.join("; ")}`);
    const path = join(dirname(jobPath), "rasters", `${page.id}.png`);
    await mkdir(dirname(path), { recursive: true });
    await sharp(pixels, { raw: { width: page.width, height: page.height, channels: 4 } })
      .png({ compressionLevel: 9, adaptiveFiltering: false }).toFile(path);
    outputs.push({ id: page.id, path: `rasters/${page.id}.png`, sha256: await checksum(path) });
    console.log(`Rendered ${page.id}`);
  }
} finally {
  map.release();
  source.close();
}
await writeFile(join(dirname(jobPath), "rendered.json"), JSON.stringify({
  jobs_sha256: await checksum(jobPath),
  node: process.version,
  system_tools: (await readFile("/opt/ck-atlas-tool-versions.txt", "utf8")) +
    "\nJavaScript packages:\n" + Object.entries(packages.dependencies)
      .sort(([a], [b]) => a.localeCompare(b, "en")).map(([name, version]) => `${name}==${version}`).join("\n") + "\n",
  files: outputs,
}, null, 2) + "\n");
