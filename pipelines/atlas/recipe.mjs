import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

export function rendererFingerprint(root = new URL("./", import.meta.url)) {
  const { files } = JSON.parse(readFileSync(new URL("recipe.json", root), "utf8"));
  if (!Array.isArray(files) || new Set(files).size !== files.length ||
      !files.includes("recipe.json")) throw new Error("Invalid renderer recipe");
  const hash = createHash("sha256");
  for (const name of files) {
    if (!/^[a-z0-9_.-]+$/.test(name) || name === "." || name === "..") {
      throw new Error("Invalid renderer recipe filename");
    }
    hash.update(name + "\0");
    hash.update(readFileSync(new URL(name, root)));
  }
  return hash.digest("hex");
}
