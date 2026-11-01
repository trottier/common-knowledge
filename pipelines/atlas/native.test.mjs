import { expect, test } from "bun:test";

test("native renderer draws and repeats an offline fixture", () => {
  const runs = [];
  for (let i = 0; i < 2; i++) {
    const result = Bun.spawnSync(["xvfb-run", "-a", "--server-args=-screen 0 1920x2400x24 -nolisten tcp",
      "node", "native-smoke.mjs"], { cwd: import.meta.dir });
    expect(result.exitCode, result.stderr.toString()).toBe(0);
    const output = JSON.parse(result.stdout.toString());
    expect(output.hashes[0]).toMatch(/^[0-9a-f]{64}$/);
    expect(output.hashes[0]).toBe(output.hashes[1]);
    runs.push(output.hashes[0]);
  }
  expect(runs[0]).toBe(runs[1]);
}, 60000);
