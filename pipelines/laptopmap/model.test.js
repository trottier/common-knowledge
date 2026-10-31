import { test, expect } from "bun:test";
import { coordinates, localSource, mapStyle, validateArchive } from "./model.js";

test("coordinate input handles western longitude and rejects empty or nonfinite values", () => {
  expect(coordinates("38.5", "-121.4")).toEqual([-121.4, 38.5]);
  for (const args of [["", "0"], ["85.1", "0"], ["0", "181"], ["NaN", "0"]]) {
    expect(() => coordinates(...args)).toThrow();
  }
});
test("map uses only the file protocol, local fonts and the narrow dataset", () => {
  const style = mapStyle("local-1", 12);
  expect(style.glyphs).toBeUndefined();
  expect(style.sprite).toBeUndefined();
  expect(style.sources.basemap.url).toBe("pmtiles://local-1");
  expect(new Set(style.layers.map((layer) => layer["source-layer"]).filter(Boolean)))
    .toEqual(new Set(["water", "roads", "places"]));
});
test("archive selection requires this build's dataset, epoch, source and encoding", () => {
  const settings = { dataset_id: "test", max_zoom: 12, source_date_epoch: 10, source_version: "source" };
  const header = { tileType: 1, maxZoom: 12 };
  const metadata = { ck_dataset: "test", source_date_epoch: 10, ck_source_version: "source" };
  validateArchive(header, metadata, settings);
  expect(() => validateArchive(header, { ...metadata, source_date_epoch: 11 }, settings)).toThrow();
  expect(() => validateArchive({ ...header, tileType: 2 }, metadata, settings)).toThrow();
});
test("reselecting same-named files gives distinct bound file sources", async () => {
  class Source { constructor(file) { this.file = file; } getBytes() { return this.file; } }
  const one = localSource("file-one", "local-1", Source), two = localSource("file-two", "local-2", Source);
  expect(one.getKey()).not.toBe(two.getKey());
  expect(one.getBytes()).toBe("file-one");
  expect(two.getBytes()).toBe("file-two");
});
