import { describe, expect, test } from "bun:test";
import { safeURL, entryURLs, manifestURL, downloadEntries, cleanPath, fileURL, fileType, folderEntries, formatBytes, indexFiles, isHidden } from "./app.js";

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

test("hosted and local URL contracts preserve transport names and reject external execution", () => {
  expect(manifestURL(null)).toBe("/api/drive");
  expect(manifestURL("drive.json")).toBe("drive.json");
  const entry = {path:"folder/index.html", url:"files/folder/index.html.download", download_url:"downloads/folder/index.html.download"};
  expect(entryURLs(entry)).toEqual({url:entry.url, download:entry.download_url});
  expect(entryURLs({path:"a.pdf"})).toEqual({url:"/files/a.pdf", download:"/files/a.pdf"});
  for(const bad of ["https://example.com/a", "http://localhost/a", "javascript:alert(1)", "data:text/html,test", "//evil.test/a", "/\\evil.test/a", "\\evil.test/a", " a.pdf", "a\n.pdf", ""]) {
    expect(() => safeURL(bad)).toThrow("Unsafe");
    expect(() => indexFiles([{path:"a.pdf",kind:"file",url:bad}])).toThrow();
    expect(() => entryURLs({path:"a.pdf",download_url:bad})).toThrow();
  }
  expect(new URL(safeURL("files/a%20b.pdf"),"https://preview.test/nested/").pathname).toBe("/nested/files/a%20b.pdf");
});
test("download cards resolve only actual visible PDFs and actual inventory sizes", () => {
 const entries=indexFiles([{path:"map.pdf",kind:"file",size_bytes:123},{path:"app.apk",kind:"file",size_bytes:20},{path:"BACKUP/map.pdf",kind:"file",size_bytes:10}]);
 expect(downloadEntries([{path:"map.pdf",size_bytes:999}],entries)[0].size_bytes).toBe(123);
 expect(downloadEntries(undefined,entries)).toEqual([]);
 for(const values of [[{path:"missing.pdf"}], ["app.apk"], ["BACKUP/map.pdf"], ["map.pdf","map.pdf"]]) expect(()=>downloadEntries(values,entries)).toThrow();
 expect(()=>downloadEntries({},entries)).toThrow();
});
