import { describe, expect, test } from "bun:test";
import { cleanPath, fileURL, fileType, folderEntries, formatBytes, indexFiles, isHidden } from "./app.js";

describe("real inventory navigation", () => {
  const files = [
    {path: "3_MAPS_AND_PLACES/RI/Bristol County/Bristol County 02806,02809,02885.pdf", kind: "file", size_bytes: 1234},
    {path: "1_START/简体中文/01_START.pdf", kind: "file", size_bytes: 10},
    {path: "README.TXT", kind: "file", size_bytes: 0},
    {path: "BACKUP/1_START/en/01_START.pdf", kind: "file", size_bytes: 10},
  ];
  test("infers only actual parent folders and preserves complete ZIP names", () => {
    const entries = indexFiles(files);
    expect(folderEntries(entries, "").map(row => row.name)).toEqual(["1_START", "3_MAPS_AND_PLACES", "README.TXT"]);
    expect(folderEntries(entries, "3_MAPS_AND_PLACES/RI/Bristol County")[0].name).toBe("Bristol County 02806,02809,02885.pdf");
    expect(entries.has("2_VIDEOS")).toBe(false);
  });
  test("search is confined to the current folder", () => {
    const entries = indexFiles(files);
    expect(folderEntries(entries, "", "02885")).toEqual([]);
    expect(folderEntries(entries, "3_MAPS_AND_PLACES/RI/Bristol County", "02885")).toHaveLength(1);
  });
  test("backup and custom hidden descendants stay hidden unless requested", () => {
    const entries = indexFiles([...files, {path: "private", kind: "directory", hidden: true}, {path: "private/a.txt", kind: "file", hidden: false}]);
    expect(folderEntries(entries, "").some(row => row.name === "BACKUP")).toBe(false);
    expect(folderEntries(entries, "", "", true).some(row => row.name === "BACKUP")).toBe(true);
    expect(folderEntries(entries, "private")).toEqual([]);
    expect(isHidden({path: "folder/.metadata/file"})).toBe(true);
  });
  test("inconsistent inventories fail visibly", () => {
    expect(() => indexFiles([...files, files[0]])).toThrow("Duplicate");
    expect(() => indexFiles([{path: "a", kind: "file"}, {path: "a/b", kind: "file"}])).toThrow("conflicts");
    expect(() => indexFiles([{path: "a", kind: "symlink"}])).toThrow("Unknown");
    expect(() => indexFiles(null)).toThrow();
  });
});

test("file URLs preserve Unicode, spaces, percent signs, and fragment characters", () => {
  expect(fileURL("1_START/简体中文/Read #1%.pdf")).toBe("/files/1_START/%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87/Read%20%231%25.pdf");
});
for (const path of ["/etc/passwd", "../x", "a/../x", "a//b", "a/./b", "a\\b", "a\u0000b"]) {
  test(`rejects unsafe inventory path ${JSON.stringify(path)}`, () => expect(() => cleanPath(path)).toThrow());
}
test("only supported inert previews are classified; programs stay binary", () => {
  expect(fileType({name: "x.pdf", kind: "file"}).type).toBe("pdf");
  expect(fileType({name: "x.MP4", kind: "file"}).type).toBe("video");
  expect(fileType({name: "README.TXT", kind: "file"}).type).toBe("text");
  for (const name of ["app.apk", "program.exe", "launch.command", "index.html", "script.js"]) expect(fileType({name, kind: "file"}).type).toBe("binary");
});
test("sizes remain actual decimal bytes, including empty and unavailable files", () => {
  expect(formatBytes(0)).toBe("0 B");
  expect(formatBytes(1234)).toBe("1.2 KB");
  expect(formatBytes(10_000_000)).toBe("10 MB");
  expect(formatBytes(null)).toBe("Size unavailable");
  expect(formatBytes(-1)).toBe("Size unavailable");
});
