/** Original synthetic geometry; exercise the real native renderer without maps or networking. */
import { createRequire } from "node:module";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { promisify } from "node:util";
import sharp from "sharp";
import { resource } from "./source.mjs";
import { loadStyleWithGlyphs } from "./glyphs.mjs";

const require = createRequire(import.meta.url);
const native = require("@maplibre/maplibre-gl-native");
const fontnik = require("fontnik");
const range = promisify(fontnik.range);
const font = await readFile("/opt/ck-atlas-test-font.ttf");
const failures = [];
let requestedGlyphs = 0;
const map = new native.Map({ ratio: 1, request(request, callback) {
  Promise.resolve().then(async () => {
    const glyph = resource(request.url);
    if (glyph.kind !== "glyph") throw new Error("Unexpected fixture resource");
    requestedGlyphs++;
    return range({ font, start: glyph.start, end: glyph.end });
  }).then(data => callback(null, { data })).catch(error => {
    failures.push(error.message);
    callback(error);
  });
}});
const style = { version: 8, glyphs: "ck-font://{fontstack}/{range}.pbf",
  sources: { fixture: { type: "geojson", data: { type: "Feature", properties: {},
    geometry: { type: "Point", coordinates: [-71, 42] } } } },
  layers: [
    { id: "paper", type: "background", paint: { "background-color": "#faf9f4" } },
    { id: "dot", type: "circle", source: "fixture", paint: { "circle-radius": 30,
      "circle-color": "#000000" } },
    { id: "label", type: "symbol", source: "fixture", layout: {
      "text-field": "Offline atlas fixture", "text-font": ["Noto Sans Regular"],
      "text-size": 24, "text-offset": [0, 3] } },
  ],
};
const hashes = [];
try {
  await loadStyleWithGlyphs(map, fontnik, font, style);
  for (let i = 0; i < 2; i++) {
    const pixels = await new Promise((accept, reject) => map.render({ width: 512,
      height: 512, center: [-71, 42], zoom: 3, bearing: 0, pitch: 0 },
    (error, data) => error ? reject(error) : accept(data)));
    if (failures.length) throw new Error(failures.join("; "));
    if (pixels[(256 * 512 + 256) * 4] !== 0) throw new Error("Fixture point was not drawn");
    const png = await sharp(pixels, { raw: { width: 512, height: 512, channels: 4 } })
      .png({ compressionLevel: 9, adaptiveFiltering: false }).toBuffer();
    hashes.push(createHash("sha256").update(png).digest("hex"));
  }
} finally {
  map.release();
}
if (hashes[0] !== hashes[1]) throw new Error("Native rendering changed between identical jobs");
if (!requestedGlyphs) throw new Error("Fixture font was not requested");
console.log(JSON.stringify({ hashes }));
