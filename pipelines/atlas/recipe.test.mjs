import { expect, test } from "bun:test";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { rendererFingerprint } from "./recipe.mjs";

test("renderer identity detects changed code and rejects escaping paths", () => {
  const folder = mkdtempSync(join(tmpdir(), "ck-renderer-"));
  try {
    const root = pathToFileURL(folder + "/");
    writeFileSync(join(folder, "recipe.json"), JSON.stringify({ files: ["recipe.json", "source.mjs"] }));
    writeFileSync(join(folder, "source.mjs"), "first");
    const original = rendererFingerprint(root);
    writeFileSync(join(folder, "source.mjs"), "second");
    expect(rendererFingerprint(root)).not.toBe(original);
    writeFileSync(join(folder, "recipe.json"), JSON.stringify({ files: ["recipe.json", "../escape"] }));
    expect(() => rendererFingerprint(root)).toThrow("filename");
  } finally { rmSync(folder, { recursive: true }); }
});
