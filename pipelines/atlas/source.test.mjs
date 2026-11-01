import { expect, test } from "bun:test";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { LocalSource, resource } from "./source.mjs";

test("local byte ranges clamp at EOF and reject invalid positions", async () => {
  const folder = mkdtempSync(join(tmpdir(), "ck-range-"));
  const file = join(folder, "synthetic");
  writeFileSync(file, Buffer.from([10, 20, 30, 40]));
  const source = new LocalSource(file, "fixture");
  try {
    expect([...new Uint8Array((await source.getBytes(1, 2)).data)]).toEqual([20, 30]);
    expect([...new Uint8Array((await source.getBytes(2, 20)).data)]).toEqual([30, 40]);
    await expect(source.getBytes(-1, 2)).rejects.toThrow();
    await expect(source.getBytes(5, 1)).rejects.toThrow();
  } finally {
    source.close();
    rmSync(folder, { recursive: true });
  }
});

test("renderer resource policy rejects network URLs and traversal", () => {
  expect(resource("ck-tile://2/1/3")).toEqual({ kind: "tile", z: 2, x: 1, y: 3 });
  expect(resource("ck-font://Noto%20Sans/0-255.pbf").kind).toBe("glyph");
  for (const value of ["https://example.test/tile", "file:///etc/passwd",
    "ck-tile://2/4/1", "ck-font://font/1-256.pbf", "ck-font://../0-256.pbf"]) {
    expect(() => resource(value)).toThrow();
  }
});
