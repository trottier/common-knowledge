import { promisify } from "node:util";

/** Prime every supported glyph independently before vector-tile layout.
 * Separate labels avoid shaping/normalization across adjacent Unicode points.
 * Keep its world tile resident so removing the last glyph requester cannot
 * evict the primed glyph atlas. Published viewports must exclude its origin.
 */
export async function loadStyleWithGlyphs(map, fontnik, font, style) {
  const faces = await promisify(fontnik.load)(font);
  const points = faces[0].points.filter(point => point >= 32 && point <= 65535)
    .sort((a, b) => a - b);
  map.load({ version: 8, glyphs: style.glyphs,
    sources: { warmup: { type: "geojson", maxzoom: 0, data: { type: "FeatureCollection",
      features: points.map(point => ({ type: "Feature", id: point,
        properties: { glyph: String.fromCodePoint(point) },
        geometry: { type: "Point", coordinates: [0, 0] } })) } } },
    layers: [{ id: "warmup", type: "symbol", source: "warmup", layout: {
      "text-field": ["get", "glyph"], "text-font": ["Noto Sans Regular"],
      "text-size": 1, "text-allow-overlap": true, "text-ignore-placement": true,
      "symbol-sort-key": ["id"] } }],
  });
  await new Promise((accept, reject) => map.render({ width: 512, height: 512,
    center: [0, 0], zoom: 0 }, (error, pixels) => error ? reject(error) : accept(pixels)));
  for (const [key, value] of Object.entries(style.sources)) map.addSource(key, value);
  for (const layer of style.layers) map.addLayer(layer);
}

/** Include a generous label margin; the original warmup must stay off page. */
export function excludesWarmup(page) {
  const world = 512 * 2 ** page.zoom;
  const [longitude, latitude] = page.center;
  const x = Math.abs(((longitude + 540) % 360) - 180) / 360 * world;
  const radians = latitude * Math.PI / 180;
  const y = Math.abs(Math.log(Math.tan(Math.PI / 4 + radians / 2))) / (2 * Math.PI) * world;
  return x > page.width / 2 + 256 || y > page.height / 2 + 256;
}
