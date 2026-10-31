import { promisify } from "node:util";

/** Prime one font before asynchronous vector-tile layout allocates glyphs.
 * Loading glyphs tile by tile can change atlas packing and tiny SDF edge values.
 * This discarded, original fixture supplies the font's BMP glyphs in one batch.
 */
export async function loadStyleWithGlyphs(map, fontnik, font, style) {
  const faces = await promisify(fontnik.load)(font);
  const points = faces[0].points.filter(point => point >= 32 && point <= 65535)
    .sort((a, b) => a - b);
  map.load({ version: 8, glyphs: style.glyphs,
    sources: { warmup: { type: "geojson", data: { type: "Feature", properties: {},
      geometry: { type: "Point", coordinates: [0, 0] } } } },
    layers: [{ id: "warmup", type: "symbol", source: "warmup", layout: {
      "text-field": String.fromCodePoint(...points), "text-font": ["Noto Sans Regular"],
      "text-size": 1, "text-max-width": 500 } }],
  });
  await new Promise((accept, reject) => map.render({ width: 512, height: 512,
    center: [0, 0], zoom: 0 }, (error, pixels) => error ? reject(error) : accept(pixels)));
  map.removeLayer("warmup");
  map.removeSource("warmup");
  for (const [key, value] of Object.entries(style.sources)) map.addSource(key, value);
  for (const layer of style.layers) map.addLayer(layer);
}
