import { expect, test } from "bun:test";
import { excludesWarmup, loadStyleWithGlyphs } from "./glyphs.mjs";

test("warmup supplies independent glyphs without cross-character shaping", async () => {
  let warmup;
  const events = [];
  const map = {
    load(style) { warmup = style; },
    render(options, callback) { events.push("render"); callback(null, Buffer.alloc(0)); },
    removeLayer(id) { events.push(`remove-layer:${id}`); },
    removeSource(id) { events.push(`remove-source:${id}`); },
    addSource(id) { events.push(`add-source:${id}`); },
    addLayer(layer) { events.push(`add-layer:${layer.id}`); },
  };
  const fontnik = { load(_font, callback) { callback(null, [{ points: [233, 31, 65, 32, 0x1F600] }]); } };
  await loadStyleWithGlyphs(map, fontnik, Buffer.alloc(0), {
    glyphs: "ck-font://font/{range}.pbf", sources: { basemap: {} }, layers: [{ id: "roads" }],
  });
  expect(warmup.sources.warmup.data.features.map((feature) => feature.id)).toEqual([32, 65, 233]);
  expect(warmup.sources.warmup.data.features.map((feature) => feature.properties.glyph)).toEqual([" ", "A", "é"]);
  expect(warmup.layers[0].layout["text-allow-overlap"]).toBe(true);
  expect(warmup.layers[0].layout["text-field"]).toEqual(["get", "glyph"]);
  expect(warmup.sources.warmup.maxzoom).toBe(0);
  expect(events).toEqual(["render", "add-source:basemap", "add-layer:roads"]);
});

test("published viewports exclude the resident priming geometry", () => {
  expect(excludesWarmup({ center: [-71, 42], zoom: 3, width: 512, height: 512 })).toBe(true);
  expect(excludesWarmup({ center: [0, 0], zoom: 3, width: 512, height: 512 })).toBe(false);
  expect(excludesWarmup({ center: [-71, 42], zoom: 0, width: 1920, height: 2400 })).toBe(false);
  expect(excludesWarmup({ center: [180, 0], zoom: 3, width: 512, height: 512 })).toBe(true);
});
