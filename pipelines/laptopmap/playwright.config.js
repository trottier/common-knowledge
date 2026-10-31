import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "browser.spec.js",
  workers: 1,
  use: {
    browserName: "chromium",
    launchOptions: {
      executablePath: process.env.CK_CHROMIUM_EXECUTABLE || undefined,
      args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
    },
    viewport: { width: 1200, height: 900 },
  },
});
